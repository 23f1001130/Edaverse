"""One-time, reviewed setup: trust only this repository's main branch.

Run in Azure Cloud Shell with the Edaverse subscription selected. Creates a
managed identity, a federated credential, and an app-scoped read/update role.
It creates no client secret and does not read/copy application credentials.
"""
import json
import subprocess

REPOSITORY = "23f1001130/Edaverse"
RESOURCE_GROUP = "edaverse-rg"
APP = "edaverse-api"
IDENTITY = "edaverse-github-deploy"
ISSUER = "https://token.actions.githubusercontent.com"
SUBJECT = f"repo:{REPOSITORY}:ref:refs/heads/main"
ACTIONS = ["Microsoft.App/containerApps/read", "Microsoft.App/containerApps/write"]


def az(*arguments):
    result = subprocess.run(["az", *arguments, "--output", "json", "--only-show-errors"], text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError("Azure setup failed: " + result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def setup():
    account = az("account", "show")
    subscription = account["id"]
    group = f"/subscriptions/{subscription}/resourceGroups/{RESOURCE_GROUP}"
    resource = group + f"/providers/Microsoft.App/containerApps/{APP}"
    # Verify the existing app before creating any identity or permission.
    app = az("rest", "--method", "get", "--uri", "https://management.azure.com" + resource + "?api-version=2025-07-01")
    identities = az("identity", "list", "--resource-group", RESOURCE_GROUP)
    identity = next((item for item in identities if item["name"] == IDENTITY), None)
    if identity is None:
        identity = az("identity", "create", "--resource-group", RESOURCE_GROUP, "--name", IDENTITY, "--location", app["location"])
    credentials = az("identity", "federated-credential", "list", "--resource-group", RESOURCE_GROUP, "--identity-name", IDENTITY)
    credential = next((item for item in credentials if item["name"] == "github-main"), None)
    expected = {"issuer": ISSUER, "subject": SUBJECT, "audiences": ["api://AzureADTokenExchange"]}
    if credential:
        if any(credential.get(key) != value for key, value in expected.items()):
            raise RuntimeError("An existing github-main trust differs. Review it before changing access.")
    else:
        az("identity", "federated-credential", "create", "--resource-group", RESOURCE_GROUP,
           "--identity-name", IDENTITY, "--name", "github-main", "--issuer", ISSUER,
           "--subject", SUBJECT, "--audiences", "api://AzureADTokenExchange")
    role_name = "Edaverse image deployer"
    roles = [role for role in az("role", "definition", "list", "--custom-role-only", "true", "--scope", group)
             if role.get("roleName") == role_name]
    if len(roles) > 1:
        raise RuntimeError("More than one deployment role has this name. Review before assigning access.")
    if roles:
        permissions = roles[0]["permissions"]
        if (len(permissions) != 1 or {action.lower() for action in permissions[0].get("actions", [])} != {action.lower() for action in ACTIONS}
                or permissions[0].get("dataActions") or permissions[0].get("notActions")
                or [scope.lower() for scope in roles[0]["assignableScopes"]] != [group.lower()]):
            raise RuntimeError("The existing deployment role differs. Review it before assigning access.")
        role_id = roles[0]["id"]
    else:
        created = az("role", "definition", "create", "--role-definition", json.dumps({
            "Name": role_name, "IsCustom": True,
            "Description": "Read and update the existing Edaverse container app for GitHub releases.",
            "Actions": ACTIONS, "NotActions": [], "DataActions": [], "NotDataActions": [],
            "AssignableScopes": [group]}))
        # Azure generates this identifier; a caller-supplied Id is not preserved.
        role_id = created["id"]
    assignments = az("role", "assignment", "list", "--assignee-object-id", identity["principalId"],
                     "--scope", resource, "--role", role_id)
    if not assignments:
        az("role", "assignment", "create", "--assignee-object-id", identity["principalId"],
           "--assignee-principal-type", "ServicePrincipal", "--role", role_id, "--scope", resource)
    print("One-time GitHub deployment identity configured for this app only.")
    print("These identifiers are not passwords or API keys. Send these three lines back:")
    print("AZURE_CLIENT_ID=" + identity["clientId"])
    print("AZURE_TENANT_ID=" + account["tenantId"])
    print("AZURE_SUBSCRIPTION_ID=" + subscription)


if __name__ == "__main__":
    setup()
