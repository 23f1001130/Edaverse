"""Verify deployment payloads and rollback without contacting a cloud account."""
import copy
import importlib.util
from pathlib import Path

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deploy = load("deploy_azure")


def app():
    return {"name": "edaverse-api", "location": "uaenorth", "properties": {
        "configuration": {"activeRevisionsMode": "Single", "secrets": [{"name": "database"}],
                          "ingress": {"fqdn": "edaverse-api.example.uaenorth.azurecontainerapps.io"}},
        "template": {"revisionSuffix": "previous", "scale": {"minReplicas": 0, "maxReplicas": 1},
                     "containers": [{"name": "edaverse-api", "image": "ghcr.io/23f1001130/edaverse-api:sha-" + "b" * 40,
                         "resources": {"cpu": 1, "memory": "2Gi"},
                         "env": [{"name": "MONGODB_URI", "secretRef": "database"}]}]}}}


def test_patch_changes_only_image_and_revision_without_copying_secrets():
    original = app()
    payload, previous = deploy.image_patch(original, "edaverse-api", "new-image", "new-suffix")
    assert previous == "ghcr.io/23f1001130/edaverse-api:sha-" + "b" * 40
    assert "configuration" not in payload["properties"]
    template = payload["properties"]["template"]
    expected = copy.deepcopy(original["properties"]["template"])
    expected["revisionSuffix"] = "new-suffix"
    expected["containers"][0]["image"] = "new-image"
    assert template == expected
    assert original["properties"]["template"]["containers"][0]["image"] == previous


def test_multiple_revision_mode_is_rejected_before_patch():
    original = app()
    original["properties"]["configuration"]["activeRevisionsMode"] = "Multiple"
    with pytest.raises(ValueError, match="Single"):
        deploy.image_patch(original, "edaverse-api", "new-image", "suffix")


@pytest.mark.parametrize("fail_new_health", [False, True])
def test_rollout_verifies_version_and_restores_image_on_failure(monkeypatch, fail_new_health):
    current = app()
    patches, health_calls = [], []
    sha = "a" * 40

    def arm(method, url, payload=None):
        if method == "patch":
            patches.append(copy.deepcopy(payload))
            current["properties"]["template"] = payload["properties"]["template"]
        return copy.deepcopy(current)

    def health(base, version=None):
        health_calls.append(version)
        if version and fail_new_health:
            raise TimeoutError("New version failed")

    monkeypatch.setattr(deploy, "arm", arm)
    monkeypatch.setattr(deploy, "check_health", health)
    monkeypatch.setattr(deploy, "wait_ready", lambda *args: None)
    args = ("/subscriptions/test/resourceGroups/edaverse-rg/providers/Microsoft.App/containerApps/edaverse-api",
            "edaverse-api", f"ghcr.io/23f1001130/edaverse-api:sha-{sha}", sha, "123", "1")
    if fail_new_health:
        with pytest.raises(RuntimeError, match="previous image was restored"):
            deploy.deploy(*args)
        assert len(patches) == 2
        assert patches[-1]["properties"]["template"]["containers"][0]["image"] == "ghcr.io/23f1001130/edaverse-api:sha-" + "b" * 40
        assert health_calls == [None, sha, None]
    else:
        deploy.deploy(*args)
        assert len(patches) == 1 and health_calls == [None, sha]


def test_setup_limits_trust_to_main_and_role_to_one_app(monkeypatch, capsys):
    setup = load("setup_azure_deploy")
    calls = []

    def az(*args):
        calls.append(args)
        if args[:2] == ("account", "show"):
            return {"id": "subscription-id", "tenantId": "tenant-id"}
        if args[0] == "rest":
            return {"location": "uaenorth"}
        if args[:2] == ("identity", "create"):
            return {"clientId": "client-id", "principalId": "principal-id"}
        return []

    monkeypatch.setattr(setup, "az", az)
    setup.setup()
    federation = next(call for call in calls if call[:3] == ("identity", "federated-credential", "create"))
    assert federation[federation.index("--subject") + 1] == "repo:23f1001130/Edaverse:ref:refs/heads/main"
    role = next(call for call in calls if call[:3] == ("role", "definition", "create"))
    import json
    definition = json.loads(role[role.index("--role-definition") + 1])
    assert set(definition["Actions"]) == {"Microsoft.App/containerApps/read", "Microsoft.App/containerApps/write"}
    assignment = next(call for call in calls if call[:3] == ("role", "assignment", "create"))
    assert assignment[assignment.index("--scope") + 1] == "/subscriptions/subscription-id/resourceGroups/edaverse-rg/providers/Microsoft.App/containerApps/edaverse-api"
    assert "AZURE_CLIENT_ID=client-id" in capsys.readouterr().out


def test_unknown_mutable_previous_image_is_rejected_without_deploying(monkeypatch):
    before = app()
    before["properties"]["template"]["containers"][0]["image"] = "ghcr.io/23f1001130/edaverse-api:latest"
    monkeypatch.setattr(deploy, "arm", lambda method, *args: before if method == "get" else pytest.fail("Must not deploy without a rollback image"))
    monkeypatch.setattr(deploy, "check_health", lambda *args: {})
    sha = "a" * 40
    with pytest.raises(ValueError, match="Pin the existing app"):
        deploy.deploy("/subscriptions/test", "edaverse-api", f"ghcr.io/23f1001130/edaverse-api:sha-{sha}", sha, "1", "1")


def test_readiness_does_not_accept_an_older_ready_revision(monkeypatch):
    snapshots = iter([
        {"properties": {"provisioningState": "Succeeded", "latestRevisionName": "new", "latestReadyRevisionName": "old"}},
        {"properties": {"provisioningState": "Succeeded", "latestRevisionName": "new", "latestReadyRevisionName": "new"}},
    ])
    calls = []
    monkeypatch.setattr(deploy, "arm", lambda *args: calls.append(True) or next(snapshots))
    monkeypatch.setattr(deploy.time, "sleep", lambda *args: None)
    deploy.wait_ready("url", "new")
    assert len(calls) == 2
