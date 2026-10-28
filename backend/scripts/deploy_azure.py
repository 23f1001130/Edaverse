"""Deploy an already-tested public image without replacing app configuration.

Uses Azure CLI's authenticated ARM transport. Never reads application secrets.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

API_VERSION = "2025-07-01"


def arm(method, url, payload=None):
    command = ["az", "rest", "--method", method, "--uri", url, "--output", "json", "--only-show-errors"]
    with tempfile.TemporaryDirectory() as temporary:
        if payload is not None:
            path = Path(temporary) / "patch.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            path.chmod(0o600)
            command += ["--body", "@" + str(path), "--headers", "Content-Type=application/json"]
        response = subprocess.run(command, text=True, capture_output=True, timeout=90)
    if response.returncode:
        raise RuntimeError("Azure resource request failed. Check the workflow's Azure login and the app Activity log.")
    return json.loads(response.stdout) if response.stdout.strip() else {}


def image_patch(app, container_name, image, suffix):
    if app.get("properties", {}).get("configuration", {}).get("activeRevisionsMode", "Single") != "Single":
        raise ValueError("Automatic rollout requires the app's Single revision mode.")
    template = copy.deepcopy(app["properties"]["template"])
    targets = [container for container in template["containers"] if container["name"] == container_name]
    if len(targets) != 1:
        raise ValueError("The configured Azure container name was not found uniquely.")
    previous = targets[0]["image"]
    targets[0]["image"] = image
    template["revisionSuffix"] = suffix
    return {"location": app["location"], "properties": {"template": template}}, previous


def wait_ready(url, revision, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app = arm("get", url)
        properties = app.get("properties", {})
        state = properties.get("provisioningState")
        if state in ("Failed", "Canceled"):
            raise RuntimeError("Azure could not provision the new revision.")
        if (state == "Succeeded" and properties.get("latestRevisionName") == revision
                and properties.get("latestReadyRevisionName") == revision):
            return
        time.sleep(5)
    raise TimeoutError("The new Azure revision did not become ready in time.")


def check_health(base, version=None, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(base + "/health", timeout=10) as response:
                data = json.load(response)
            if (data.get("status") == "ok" and "mongodb" in data.get("storage", "")
                    and (version is None or data.get("version") == version)):
                return data
        except (OSError, ValueError, URLError):
            pass
        time.sleep(5)
    raise TimeoutError("The release did not pass the public health, MongoDB and version checks.")


def deploy(resource_id, container, image, sha, run_id, attempt):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("A full Git commit SHA is required.")
    if image != f"ghcr.io/23f1001130/edaverse-api:sha-{sha}":
        raise ValueError("Only this repository's immutable release image can be deployed.")
    suffix = f"gh-{sha[:12]}-{run_id}-{attempt}"
    if not re.fullmatch(r"[a-z0-9-]{1,50}", suffix):
        raise ValueError("Invalid deployment run identifier.")
    url = f"https://management.azure.com{resource_id}?api-version={API_VERSION}"
    before = arm("get", url)
    host = before["properties"]["configuration"]["ingress"]["fqdn"]
    if not re.fullmatch(r"[a-z0-9.-]+\.azurecontainerapps\.io", host):
        raise ValueError("Expected an Azure Container Apps ingress hostname.")
    base = "https://" + host
    # Baseline must work before replacing anything; don't obscure existing outages.
    baseline = check_health(base) or {}
    payload, previous_image = image_patch(before, container, image, suffix)
    # A mutable 'latest' tag has already moved when CI publishes a new build.
    # Rollback must use an immutable image of the version actually running.
    baseline_version = baseline.get("version")
    if not re.fullmatch(r"ghcr\.io/23f1001130/edaverse-api(?::sha-[0-9a-f]{40}|@sha256:[0-9a-f]{64})", previous_image):
        if baseline_version and re.fullmatch(r"[0-9a-f]{40}", baseline_version):
            previous_image = f"ghcr.io/23f1001130/edaverse-api:sha-{baseline_version}"
        else:
            raise ValueError("Pin the existing app to a known sha-<commit> image once before enabling automatic rollback.")
    name = before["name"]
    try:
        arm("patch", url, payload)
        wait_ready(url, f"{name}--{suffix}")
        check_health(base, version=sha)
    except Exception as failure:
        current = arm("get", url)
        if current.get("properties", {}).get("template", {}).get("revisionSuffix") != suffix:
            raise RuntimeError("Release failed; the app was changed separately, so automatic rollback was skipped.") from failure
        rollback_suffix = suffix + "-rb"
        rollback, _ = image_patch(current, container, previous_image, rollback_suffix)
        arm("patch", url, rollback)
        wait_ready(url, f"{name}--{rollback_suffix}")
        check_health(base, version=baseline_version if baseline_version and re.fullmatch(r"[0-9a-f]{40}", baseline_version) else None)
        raise RuntimeError("Release verification failed. The previous image was restored successfully.") from failure
    print(f"Deployed and verified {sha[:12]} to {name}.")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"Azure deployment succeeded: `{sha}`. Public health, MongoDB and running version verified.\n")


if __name__ == "__main__":
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--resource-id", required=True)
    arguments.add_argument("--container", default="edaverse-api")
    arguments.add_argument("--image", required=True)
    arguments.add_argument("--sha", required=True)
    arguments.add_argument("--run-id", required=True)
    arguments.add_argument("--attempt", required=True)
    options = arguments.parse_args()
    deploy(options.resource_id, options.container, options.image, options.sha, options.run_id, options.attempt)
