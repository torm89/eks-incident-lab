"""Bring the whole lab up or down with one command. Works on Windows, Linux and macOS.

    uv run scripts/lab.py up                # cluster, monitoring, store, AI assistant, traffic
    uv run scripts/lab.py up --no-ai        # without the AI assistant (no Docker needed)
    uv run scripts/lab.py down              # destroy everything, including applied FIS scenarios
    uv run scripts/lab.py up --dry-run      # print the commands only

Both commands ask before OpenTofu creates or destroys anything, unless --yes is given.
`up` is safe to run again: every step applies the desired state.
Needs: backend.hcl (see README, "Local setup") and AWS credentials (AWS_PROFILE).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import boto3

import push_images

REPO_ROOT = Path(__file__).resolve().parent.parent
INFRA_DIR = REPO_ROOT / "infra"
BACKEND_CONFIG = REPO_ROOT / "backend.hcl"
FIS_SCENARIOS_DIR = REPO_ROOT / "chaos" / "scenarios" / "level-3-aws"
HELM_CHART_CACHES = [REPO_ROOT / "platform" / "monitoring" / "charts", REPO_ROOT / "platform" / "monitoring" / "crds" / "charts"]

MIN_TOFU_VERSION = (1, 10)
REQUIRED_HELM_MAJOR = 3  # kubectl's built-in kustomize does not work with Helm 4.
ROLLOUT_TIMEOUT = "7m"
CRD_TIMEOUT = "2m"
APP_NAMESPACES = ("monitoring", "retail-store", "ai-assistant")


class LabError(Exception):
    pass


# ---------------------------------------------------------------- running commands

def external_tool_env() -> dict[str, str]:
    """Environment for external tools without the uv virtualenv.

    `uv run` puts the project's Python first on PATH. Tools written in Python (e.g. the AWS CLI v1,
    used by kubectl to get EKS tokens) would then start in the wrong interpreter.
    """
    env = dict(os.environ)
    venv = env.pop("VIRTUAL_ENV", None)
    if venv:
        venv_dirs = {str(Path(venv) / "Scripts"), str(Path(venv) / "bin")}
        env["PATH"] = os.pathsep.join(entry for entry in env["PATH"].split(os.pathsep) if entry not in venv_dirs)
    return env


@dataclass
class Runner:
    dry_run: bool

    def __post_init__(self) -> None:
        self._env = external_tool_env()

    def run(self, command: list[str], cwd: Path = REPO_ROOT, stdin: str | None = None,
            capture: bool = False, check: bool = True) -> str:
        """Runs a command; output goes to the terminal unless captured. Interactive prompts work."""
        print(f"  $ {' '.join(command)}", flush=True)
        if self.dry_run:
            return ""
        executable = shutil.which(command[0], path=self._env["PATH"]) or command[0]
        result = subprocess.run([executable, *command[1:]], cwd=cwd, input=stdin, env=self._env,
                                capture_output=capture, text=True, encoding="utf-8", errors="replace")
        if check and result.returncode != 0:
            details = f"\n{result.stderr}" if capture else ""
            raise LabError(f"Command failed ({result.returncode}): {' '.join(command)}{details}")
        return result.stdout if capture else ""

    def query(self, command: list[str], cwd: Path = REPO_ROOT) -> str:
        """Read-only command whose output is needed, also in dry-run mode."""
        executable = shutil.which(command[0], path=self._env["PATH"]) or command[0]
        result = subprocess.run([executable, *command[1:]], cwd=cwd, env=self._env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise LabError(f"Command failed: {' '.join(command)}\n{result.stderr}")
        return result.stdout


def step(number: int, total: int, title: str) -> None:
    print(f"\n==> [{number}/{total}] {title}", flush=True)


# ---------------------------------------------------------------- preflight

def check_tools(runner: Runner, need_docker: bool) -> None:
    tools = ["tofu", "kubectl", "helm", "aws"] + (["docker"] if need_docker else [])
    missing = [tool for tool in tools if shutil.which(tool, path=runner._env["PATH"]) is None]
    if missing:
        raise LabError(f"Missing tools on PATH: {', '.join(missing)}")

    tofu_version = _version(runner.query(["tofu", "version"]))
    if tofu_version < MIN_TOFU_VERSION:
        raise LabError(f"OpenTofu {'.'.join(map(str, MIN_TOFU_VERSION))}+ required, found {'.'.join(map(str, tofu_version))}")
    helm_major = _version(runner.query(["helm", "version", "--short"]))[0]
    if helm_major != REQUIRED_HELM_MAJOR:
        raise LabError(f"Helm {REQUIRED_HELM_MAJOR} required (kubectl's kustomize does not work with Helm {helm_major})")
    if need_docker:
        runner.query(["docker", "info", "--format", "{{.ServerVersion}}"])  # fails if the daemon is not running


def _version(text: str) -> tuple[int, ...]:
    match = re.search(r"v?(\d+)\.(\d+)", text)
    if not match:
        raise LabError(f"Cannot read a version from: {text.strip()[:80]}")
    return int(match.group(1)), int(match.group(2))


def check_aws() -> boto3.Session:
    if not BACKEND_CONFIG.exists():
        raise LabError(f"{BACKEND_CONFIG.name} not found: copy backend.hcl.example and set your state bucket")
    session = boto3.Session()
    identity = session.client("sts").get_caller_identity()
    print(f"  AWS account {identity['Account']}, profile {session.profile_name}, region {session.region_name}")
    return session


def preflight(runner: Runner, need_docker: bool) -> boto3.Session:
    check_tools(runner, need_docker)
    return check_aws()


# ---------------------------------------------------------------- OpenTofu

def tofu_init(runner: Runner, directory: Path) -> None:
    runner.run(["tofu", "init", "-input=false", f"-backend-config={BACKEND_CONFIG}"], cwd=directory)


def tofu_apply_or_destroy(runner: Runner, directory: Path, action: str, auto_approve: bool) -> None:
    runner.run(["tofu", action] + (["-auto-approve"] if auto_approve else []), cwd=directory)


def tofu_output(runner: Runner, name: str) -> str:
    return runner.query(["tofu", "output", "-raw", name], cwd=INFRA_DIR).strip()


def applied_fis_scenarios(session: boto3.Session) -> list[Path]:
    """Level-3 scenarios whose state in S3 still holds resources."""
    bucket = re.search(r'bucket\s*=\s*"([^"]+)"', BACKEND_CONFIG.read_text(encoding="utf-8")).group(1)
    s3 = session.client("s3")
    applied = []
    for scenario in sorted(path for path in FIS_SCENARIOS_DIR.iterdir() if (path / "infra").is_dir()):
        key = f"chaos/{scenario.name}/terraform.tfstate"
        try:
            state = json.loads(s3.get_object(Bucket=bucket, Key=key)["Body"].read())
        except s3.exceptions.NoSuchKey:
            continue
        if state.get("resources"):
            applied.append(scenario / "infra")
    return applied


# ---------------------------------------------------------------- Kubernetes

def apply_kustomization(runner: Runner, path: str, with_helm: bool = False) -> None:
    if with_helm:
        for cache in HELM_CHART_CACHES:
            shutil.rmtree(cache, ignore_errors=True)  # a stale chart cache makes helm pull fail
        manifests = runner.run(["kubectl", "kustomize", "--enable-helm", path], capture=True)
        runner.run(["kubectl", "apply", "--server-side", "-f", "-"], stdin=manifests)
    else:
        runner.run(["kubectl", "apply", "-k", path])


def wait_for_rollouts(runner: Runner, namespace: str) -> None:
    if runner.dry_run:
        runner.run(["kubectl", "-n", namespace, "rollout", "status", "<each deployment and statefulset>"])
        return
    workloads = runner.query(["kubectl", "-n", namespace, "get", "deployments,statefulsets", "-o", "name"]).split()
    for workload in workloads:
        runner.run(["kubectl", "-n", namespace, "rollout", "status", workload, f"--timeout={ROLLOUT_TIMEOUT}"])


def delete_load_balancers(runner: Runner) -> None:
    """Load balancers created by Kubernetes are not in OpenTofu state and would block VPC deletion."""
    if runner.dry_run:
        return
    services = json.loads(runner.query(["kubectl", "get", "services", "-A", "-o", "json"]))["items"]
    for service in services:
        if service["spec"].get("type") == "LoadBalancer":
            metadata = service["metadata"]
            runner.run(["kubectl", "-n", metadata["namespace"], "delete", "service", metadata["name"]])


def cluster_reachable(runner: Runner) -> bool:
    try:
        runner.query(["kubectl", "get", "namespaces", "--request-timeout=10s"])
        return True
    except LabError:
        return False


# ---------------------------------------------------------------- commands

def up(runner: Runner, with_ai: bool, auto_approve: bool) -> None:
    total = 8 if with_ai else 7
    step(1, total, "Preflight checks")
    preflight(runner, need_docker=with_ai)

    step(2, total, "Cluster (OpenTofu, ~20 min on first run)")
    tofu_init(runner, INFRA_DIR)
    tofu_apply_or_destroy(runner, INFRA_DIR, "apply", auto_approve)

    step(3, total, "kubectl access")
    region = tofu_output(runner, "region") if not runner.dry_run else "<region>"
    cluster = tofu_output(runner, "cluster_name") if not runner.dry_run else "<cluster>"
    runner.run(["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster])

    step(4, total, "Monitoring (Prometheus, Grafana, Alertmanager, alerts)")
    apply_kustomization(runner, "platform/monitoring/crds", with_helm=True)
    runner.run(["kubectl", "wait", "--for=condition=Established", "crd", "--all", f"--timeout={CRD_TIMEOUT}"])
    apply_kustomization(runner, "platform/monitoring", with_helm=True)
    wait_for_rollouts(runner, "monitoring")

    step(5, total, "Retail Store")
    apply_kustomization(runner, "apps/retail-store")
    wait_for_rollouts(runner, "retail-store")

    current = 6
    if with_ai:
        step(current, total, "AI assistant (build + push images, mock LLM)")
        print("  $ uv run scripts/push_images.py")
        if not runner.dry_run:
            push_images.build_and_push(push_images.find_services())
        apply_kustomization(runner, "apps/ai-assistant/base")
        wait_for_rollouts(runner, "ai-assistant")
        current += 1

    step(current, total, "Synthetic traffic")
    apply_kustomization(runner, "traffic")
    if with_ai:
        apply_kustomization(runner, "traffic/ai-assistant")

    step(total, total, "Ready")
    print_access_hints(with_ai)


def down(runner: Runner, auto_approve: bool) -> None:
    step(1, 4, "Preflight checks")
    session = preflight(runner, need_docker=False)

    step(2, 4, "Level-3 chaos scenarios (AWS FIS)")
    scenarios = applied_fis_scenarios(session)
    if not scenarios:
        print("  none applied")
    for scenario in scenarios:
        tofu_init(runner, scenario)
        tofu_apply_or_destroy(runner, scenario, "destroy", auto_approve)

    step(3, 4, "Kubernetes resources outside OpenTofu (load balancers)")
    if cluster_reachable(runner):
        delete_load_balancers(runner)
    else:
        print("  cluster not reachable, skipped")

    step(4, 4, "Cluster (OpenTofu, ~10-15 min)")
    print("  If a node hangs in 'Terminating:Wait', EKS is draining it; it continues by itself within 30 min.")
    tofu_init(runner, INFRA_DIR)
    tofu_apply_or_destroy(runner, INFRA_DIR, "destroy", auto_approve)
    print("\nDone. Nothing billable is left from this lab, except the S3 state bucket.")


def print_access_hints(with_ai: bool) -> None:
    hints = [
        ("Grafana (dashboards 'Incident Lab / ...')", "kubectl -n monitoring port-forward svc/kube-prometheus-stack-grafana 3000:80", "http://localhost:3000"),
        ("Alertmanager", "kubectl -n monitoring port-forward svc/kube-prometheus-stack-alertmanager 9093:9093", "http://localhost:9093"),
        ("Store UI", "kubectl -n retail-store port-forward svc/ui 8080:80", "http://localhost:8080"),
    ]
    if with_ai:
        hints.append(("AI assistant API", "kubectl -n ai-assistant port-forward svc/ai-assistant 8081:80", "POST http://localhost:8081/chat"))
    for name, command, url in hints:
        print(f"  {name}:\n    {command}\n    -> {url}")
    print("\n  Pick a scenario: chaos/README.md. When done: uv run scripts/lab.py down")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bring the eks-incident-lab up or down.")
    commands = parser.add_subparsers(dest="command", required=True)
    up_parser = commands.add_parser("up", help="create the cluster and deploy everything")
    up_parser.add_argument("--no-ai", action="store_true", help="skip the AI assistant (no Docker needed)")
    down_parser = commands.add_parser("down", help="destroy everything")
    for command_parser in (up_parser, down_parser):
        command_parser.add_argument("--yes", action="store_true", help="do not ask before tofu apply/destroy")
        command_parser.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = Runner(dry_run=args.dry_run)
    started = time.monotonic()
    try:
        if args.command == "up":
            up(runner, with_ai=not args.no_ai, auto_approve=args.yes)
        else:
            down(runner, auto_approve=args.yes)
    except LabError as error:
        sys.exit(f"\nERROR: {error}")
    except KeyboardInterrupt:
        sys.exit("\nInterrupted. Run the same command again to continue: every step is safe to repeat.")
    print(f"\nFinished in {int(time.monotonic() - started) // 60} min.")


if __name__ == "__main__":
    main()
