"""Check and unit-test the alerting rules in platform/monitoring/alerts/ with promtool.

    uv run scripts/test_alerts.py

promtool reads plain Prometheus rule files, so the rule groups are first extracted from the
PrometheusRule resources into a temporary directory. Uses a local promtool if installed,
otherwise the prom/prometheus Docker image.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ALERTS_DIR = Path(__file__).resolve().parent.parent / "platform" / "monitoring" / "alerts"
PROMTOOL_IMAGE = "prom/prometheus:latest"


def extract_rule_files(target: Path) -> list[str]:
    names = []
    for resource_file in sorted(ALERTS_DIR.glob("*.yaml")):
        resource = yaml.safe_load(resource_file.read_text(encoding="utf-8"))
        (target / resource_file.name).write_text(yaml.safe_dump({"groups": resource["spec"]["groups"]}), encoding="utf-8")
        names.append(resource_file.name)
    for test_file in sorted((ALERTS_DIR / "tests").glob("*.yaml")):
        shutil.copy(test_file, target / test_file.name)
    return names


def promtool_command(workdir: Path) -> tuple[list[str], Path]:
    """Returns the promtool command prefix and the directory path as promtool sees it."""
    local = shutil.which("promtool")
    if local:
        return [local], workdir
    container_dir = Path("/rules")
    docker = ["docker", "run", "--rm", "-v", f"{workdir}:{container_dir.as_posix()}", "-w", container_dir.as_posix(),
              "--entrypoint", "promtool", PROMTOOL_IMAGE]
    return docker, container_dir


def run(command: list[str]) -> bool:
    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout + result.stderr)
    return result.returncode == 0


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        workdir = Path(temp)
        rule_files = extract_rule_files(workdir)
        test_files = sorted(path.name for path in (ALERTS_DIR / "tests").glob("*.yaml"))
        promtool, base = promtool_command(workdir)
        checked = run([*promtool, "check", "rules", *[(base / name).as_posix() for name in rule_files]])
        tested = run([*promtool, "test", "rules", *[(base / name).as_posix() for name in test_files]])
    sys.exit(0 if checked and tested else 1)


if __name__ == "__main__":
    main()
