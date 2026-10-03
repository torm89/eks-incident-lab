"""Build the images of our own services (services/*) and push them to ECR.

Run from the repository root after `tofu apply` in infra/:

    uv run scripts/push_images.py

The image tag is the service version from its pyproject.toml. The script stops if
apps/ai-assistant/base/kustomization.yaml points at a different tag, so the cluster
always runs exactly what was pushed.
"""

import base64
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import boto3
import yaml

AWS_PROFILE = "<aws-profile>"
AWS_REGION = "eu-west-1"
AWS_ACCOUNT_ID = "<account-id>"
REPOSITORY_PREFIX = "torm-eks"
REGISTRY = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVICES_DIR = REPO_ROOT / "services"
KUSTOMIZATION = REPO_ROOT / "apps" / "ai-assistant" / "base" / "kustomization.yaml"


@dataclass(frozen=True)
class Service:
    name: str
    directory: Path
    version: str

    @property
    def repository(self) -> str:
        return f"{REGISTRY}/{REPOSITORY_PREFIX}/{self.name}"

    @property
    def image(self) -> str:
        return f"{self.repository}:{self.version}"


def find_services() -> list[Service]:
    services = []
    for pyproject in sorted(SERVICES_DIR.glob("*/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
        services.append(Service(project["name"], pyproject.parent, project["version"]))
    return services


def check_kustomization(services: list[Service]) -> None:
    images = {image["name"]: image for image in yaml.safe_load(KUSTOMIZATION.read_text(encoding="utf-8"))["images"]}
    problems = []
    for service in services:
        image = images.get(service.name)
        if image is None:
            problems.append(f"{service.name}: missing from images in {KUSTOMIZATION.name}")
        elif (image.get("newName"), str(image.get("newTag"))) != (service.repository, service.version):
            problems.append(f"{service.name}: expected {service.image}, kustomization has {image.get('newName')}:{image.get('newTag')}")
    if problems:
        sys.exit("Image references out of sync:\n  " + "\n  ".join(problems))


def run(command: list[str], stdin: str | None = None) -> str:
    executable = shutil.which(command[0]) or command[0]
    result = subprocess.run([executable, *command[1:]], input=stdin, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"Command failed: {' '.join(command)}\n{result.stderr}")
    return result.stdout


def docker_login() -> None:
    # boto3 instead of the aws CLI: the CLI may live in another Python than the one `uv run` puts on PATH.
    ecr = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION).client("ecr")
    token = ecr.get_authorization_token()["authorizationData"][0]["authorizationToken"]
    username, password = base64.b64decode(token).decode().split(":", 1)
    run(["docker", "login", "--username", username, "--password-stdin", REGISTRY], stdin=password)


def main() -> None:
    services = find_services()
    check_kustomization(services)
    docker_login()
    for service in services:
        print(f"Building {service.image}")
        run(["docker", "build", "--tag", service.image, str(service.directory)])
        print(f"Pushing  {service.image}")
        run(["docker", "push", service.image])
    print("Done.")


if __name__ == "__main__":
    main()
