"""Inject and recover chaos scenarios, including a random one you have to find yourself.

    uv run scripts/chaos.py list                       # all scenarios
    uv run scripts/chaos.py inject orders-http-500     # a chosen scenario
    uv run scripts/chaos.py inject --random            # blind: a random level 1-2 scenario, name hidden
    uv run scripts/chaos.py inject --random --level 3  # blind, AWS FIS only (costs ~$0.10 per action-minute)
    uv run scripts/chaos.py reveal                     # what was injected, and when (time to detect)
    uv run scripts/chaos.py recover                    # undo the current scenario (the "cheat" button)

The current scenario is remembered in .chaos-session.json (git-ignored), so recover and reveal
need no name. Level 2 installs Chaos Mesh on first use. Level 3 creates the FIS template with
OpenTofu (free) and starts the experiment. Same cluster and AWS profile as scripts/lab.py.
"""

import argparse
import contextlib
import io
import json
import os
import random
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
import yaml

import lab

SCENARIOS_DIR = lab.REPO_ROOT / "chaos" / "scenarios"
SESSION_FILE = lab.REPO_ROOT / ".chaos-session.json"
CHAOS_JOB_NAMESPACE = "retail-store"  # chaos/base runs its Jobs here
CHAOS_MESH_CRD = "podchaos.chaos-mesh.org"
JOB_TIMEOUT = "90s"
DEFAULT_RANDOM_LEVELS = (1, 2)  # level 3 costs money and takes nodes away: only on request


@dataclass(frozen=True)
class Scenario:
    name: str
    level: int
    path: Path

    @property
    def needs_ai_assistant(self) -> bool:
        return "apps/ai-assistant" in self.readme_header

    @property
    def readme_header(self) -> str:
        readme = self.path / "README.md"
        return readme.read_text(encoding="utf-8").split("## Hypothesis")[0] if readme.exists() else ""

    @property
    def readme(self) -> str:
        return self.path.relative_to(lab.REPO_ROOT).joinpath("README.md").as_posix()


@dataclass
class Session:
    scenario: str
    level: int
    injected_at: str
    blind: bool
    experiment_id: str | None = None


# ---------------------------------------------------------------- scenarios

def find_scenarios() -> list[Scenario]:
    scenarios = []
    for level_dir in sorted(SCENARIOS_DIR.glob("level-*")):
        level = int(re.match(r"level-(\d+)", level_dir.name).group(1))
        scenarios += [Scenario(path.name, level, path) for path in sorted(level_dir.iterdir()) if path.is_dir()]
    return scenarios


def find_scenario(name: str) -> Scenario:
    for scenario in find_scenarios():
        if scenario.name == name:
            return scenario
    raise lab.LabError(f"Unknown scenario '{name}'. See: uv run scripts/chaos.py list")


def ai_assistant_deployed(runner: lab.Runner) -> bool:
    try:
        runner.query(["kubectl", "-n", "ai-assistant", "get", "deployment", "ai-assistant"])
        return True
    except lab.LabError:
        return False


def pick_random(runner: lab.Runner, levels: list[int]) -> Scenario:
    with_ai = ai_assistant_deployed(runner)
    candidates = [s for s in find_scenarios() if s.level in levels and (with_ai or not s.needs_ai_assistant)]
    if not candidates:
        raise lab.LabError(f"No scenarios for levels {levels}")
    return random.SystemRandom().choice(candidates)


# ---------------------------------------------------------------- session

def save_session(session: Session) -> None:
    SESSION_FILE.write_text(json.dumps(asdict(session), indent=2), encoding="utf-8")


def load_session() -> Session:
    if not SESSION_FILE.exists():
        raise lab.LabError("No scenario injected yet (no .chaos-session.json).")
    return Session(**json.loads(SESSION_FILE.read_text(encoding="utf-8")))


# ---------------------------------------------------------------- level 1: chaos Jobs

def job_names(runner: lab.Runner, kustomization: Path) -> list[str]:
    manifests = yaml.safe_load_all(runner.query(["kubectl", "kustomize", str(kustomization)]))
    return [doc["metadata"]["name"] for doc in manifests if doc and doc["kind"] == "Job"]


def run_chaos_jobs(runner: lab.Runner, kustomization: Path, keep_jobs: bool) -> None:
    """Runs the scenario's Job(s) once; deletes them afterwards in blind mode so their names do not give it away."""
    names = job_names(runner, kustomization)
    for name in names:  # a finished Job with the same name would block a re-run
        runner.run(["kubectl", "-n", CHAOS_JOB_NAMESPACE, "delete", "job", name, "--ignore-not-found"])
    runner.run(["kubectl", "create", "-k", str(kustomization)])
    for name in names:
        runner.run(["kubectl", "-n", CHAOS_JOB_NAMESPACE, "wait", "--for=condition=complete", f"job/{name}", f"--timeout={JOB_TIMEOUT}"])
        if not keep_jobs:
            runner.run(["kubectl", "-n", CHAOS_JOB_NAMESPACE, "delete", "job", name])


# ---------------------------------------------------------------- level 2: Chaos Mesh

def ensure_chaos_mesh(runner: lab.Runner) -> None:
    try:
        runner.query(["kubectl", "get", "crd", CHAOS_MESH_CRD])
        return
    except lab.LabError:
        pass
    print("  Installing Chaos Mesh (once per cluster, ~1-2 min)...", flush=True)
    lab.apply_kustomization(runner, "chaos/chaos-mesh/crds", with_helm=True)  # server-side: the CRDs are large
    runner.run(["kubectl", "wait", "--for=condition=Established", "crd", "--all", f"--timeout={lab.CRD_TIMEOUT}"])
    lab.apply_kustomization(runner, "chaos/chaos-mesh", with_helm=True)
    lab.wait_for_rollouts(runner, "chaos-mesh")


# ---------------------------------------------------------------- level 3: AWS FIS

def start_fis_experiment(runner: lab.Runner, scenario: Scenario) -> str:
    infra = scenario.path / "infra"
    with contextlib.redirect_stdout(io.StringIO()) if runner.quiet else contextlib.nullcontext():
        lab.configure_state_backend(lab.read_s3_backend())
    lab.tofu_init(runner, infra)
    lab.tofu_apply_or_destroy(runner, infra, "apply", auto_approve=True)  # template + IAM role only: free
    template_id = runner.query(["tofu", "output", "-raw", "experiment_template_id"], cwd=infra).strip()
    experiment = boto3.client("fis").start_experiment(experimentTemplateId=template_id, clientToken=str(uuid.uuid4()))
    return experiment["experiment"]["id"]


def stop_fis_experiment(experiment_id: str) -> None:
    fis = boto3.client("fis")
    state = fis.get_experiment(id=experiment_id)["experiment"]["state"]["status"]
    if state in ("pending", "initiating", "running"):
        fis.stop_experiment(id=experiment_id)
        print(f"  FIS experiment {experiment_id} stopped.")
    else:
        print(f"  FIS experiment {experiment_id} is already {state}. Lost nodes are replaced by the node group.")


# ---------------------------------------------------------------- commands

def inject(runner: lab.Runner, scenario: Scenario, blind: bool) -> None:
    if scenario.level == 1:
        run_chaos_jobs(runner, scenario.path / "inject", keep_jobs=not blind)
        experiment_id = None
    elif scenario.level == 2:
        ensure_chaos_mesh(runner)
        runner.run(["kubectl", "apply", "-k", str(scenario.path / "inject")])
        experiment_id = None
    else:
        experiment_id = start_fis_experiment(runner, scenario)
    now = datetime.now(timezone.utc)
    save_session(Session(scenario.name, scenario.level, now.isoformat(timespec="seconds"), blind, experiment_id))
    local_time = now.astimezone().strftime("%H:%M:%S")
    if blind:
        print(f"\nA random failure was injected at {local_time}. Find it: dashboards, alerts, kubectl, logs.")
        print("When you are done (or stuck): uv run scripts/chaos.py reveal")
    else:
        print(f"\nInjected {scenario.name} at {local_time}. Runbook: {scenario.readme}")


def recover(runner: lab.Runner, session: Session) -> None:
    scenario = find_scenario(session.scenario)
    if scenario.level == 1:
        recover_dir = scenario.path / "recover"
        if recover_dir.is_dir():
            run_chaos_jobs(runner, recover_dir, keep_jobs=True)
        else:
            print("  This scenario has no recover step: fix it the way the README describes.")
    elif scenario.level == 2:
        runner.run(["kubectl", "delete", "-k", str(scenario.path / "inject"), "--ignore-not-found"])
    else:
        stop_fis_experiment(session.experiment_id)
    SESSION_FILE.unlink(missing_ok=True)
    print(f"\nRecovered {scenario.name}. Verify the steady state on the dashboards.")


def reveal(session: Session) -> None:
    scenario = find_scenario(session.scenario)
    injected = datetime.fromisoformat(session.injected_at)
    minutes, seconds = divmod(int((datetime.now(timezone.utc) - injected).total_seconds()), 60)
    print(f"  Scenario:  {scenario.name} (level {scenario.level})")
    print(f"  Injected:  {injected.astimezone().strftime('%H:%M:%S')} ({minutes} min {seconds} s ago)")
    print(f"  Runbook:   {scenario.readme}")
    print("  Review:    switch on 'Chaos injected' at the top of the dashboard to measure time to detect.")


def list_scenarios() -> None:
    for scenario in find_scenarios():
        needs = "  (needs the AI assistant)" if scenario.needs_ai_assistant else ""
        print(f"  level {scenario.level}  {scenario.name}{needs}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inject and recover chaos scenarios of the eks-incident-lab.")
    parser.add_argument("--profile", help="AWS profile (default: the AWS_PROFILE variable); needed for level 3")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list all scenarios")
    inject_parser = commands.add_parser("inject", help="inject a scenario")
    target = inject_parser.add_mutually_exclusive_group(required=True)
    target.add_argument("scenario", nargs="?", help="scenario name, see list")
    target.add_argument("--random", action="store_true", help="pick a random scenario and do not tell which (blind mode)")
    inject_parser.add_argument("--level", type=int, action="append", choices=(1, 2, 3),
                               help=f"with --random: allowed levels, repeatable (default: {', '.join(map(str, DEFAULT_RANDOM_LEVELS))})")
    commands.add_parser("recover", help="undo the current scenario")
    commands.add_parser("reveal", help="show the current scenario and the time since injection")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.profile:
        os.environ["AWS_PROFILE"] = args.profile
    try:
        if args.command == "list":
            list_scenarios()
        elif args.command == "inject":
            blind = args.random
            runner = lab.Runner(dry_run=False, quiet=blind)
            levels = args.level or list(DEFAULT_RANDOM_LEVELS)
            if blind and 2 in levels:
                ensure_chaos_mesh(runner)  # before the pick: installing it later would reveal a level-2 scenario
            scenario = pick_random(runner, levels) if blind else find_scenario(args.scenario)
            inject(runner, scenario, blind)
        elif args.command == "recover":
            recover(lab.Runner(dry_run=False), load_session())
        else:
            reveal(load_session())
    except lab.LabError as error:
        sys.exit(f"\nERROR: {error}")


if __name__ == "__main__":
    main()
