# GitHub → Azure automatic deployment

The frontend already deploys to Cloudflare Pages. The backend workflow now builds
and tests an immutable GHCR image, then can update the existing Azure Container
App automatically after pushes to main. A one-time Azure OIDC connection must be
configured before enabling the deployment job. Until then, image publication and
manual Azure deployments continue to work.

## One-time connection

Review `backend/scripts/setup_azure_deploy.py`, then run it in Azure Cloud Shell
(Bash) with the Azure for Students subscription containing Edaverse selected.
It verifies the existing `edaverse-rg/edaverse-api` before creating anything.

The setup creates:

- A user-assigned managed identity named `edaverse-github-deploy`, in the app's
  resource group and region. It is a deployment identity, not extra app compute.
- A federated credential trusting GitHub's OIDC issuer, audience
  `api://AzureADTokenExchange`, and subject
  `repo:23f1001130/Edaverse:ref:refs/heads/main` only.
- A custom role with exactly `Microsoft.App/containerApps/read` and
  `Microsoft.App/containerApps/write`, assigned only to the existing app resource.
  There is no subscription-wide Contributor grant, secret-listing permission,
  delete permission, database permission or role-assignment permission.

App-update permission is still powerful: trusted main-branch workflows can deploy
code that runs with this app's existing runtime credentials. Protect main and
review workflow changes. The identity does not get added to the app's runtime.
The setup deliberately stops if an existing named trust or role differs.

It needs Azure rights to create managed identities/custom roles and assign the
role. If those rights are unavailable, stop and have the subscription administrator
review the scoped connection; do not substitute a broader role automatically.

The setup prints three identifiers, not passwords or API keys. Save them as GitHub
repository Actions **variables**:

| Variable | Source |
| --- | --- |
| `AZURE_CLIENT_ID` | Managed identity client ID printed by setup |
| `AZURE_TENANT_ID` | Tenant ID printed by setup |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID printed by setup |
| `AZURE_DEPLOY_ENABLED` | `true`, after reviewing the connection |

Then run the Backend container workflow once on main. After its first successful
Azure deployment, normal pushes to main that change backend code deploy
automatically. `workflow_dispatch` also permits a manual rebuild/deploy of main.
PR workflows only test, with no Azure ID-token permission or production deployment.

## Rollout and rollback

The app must use Single revision mode, as in the current deployment. Before the
first automatic deployment, its current image must be pinned to a known immutable
`sha-<full-commit>` tag or digest. A legacy `latest` image with no running-version
field cannot be used as a safe rollback target because publishing moves that tag.
If the app uses one, pin the last known working image once in the portal first.
After this workflow has deployed a versioned image, it can identify the running
commit even if someone later selects `latest`.

The workflow:

1. Builds with the commit in `APP_VERSION`; `/health` reports that version.
2. Tests HTTP upload, progressive full-data charts, caching and native Excel
   parsing in the non-root Linux container. Regression tests also run against the
   built image; temporary test tools and mounted tests are not published.
3. Publishes `sha-<commit>` and `latest` only after these checks pass.
4. Obtains a short-lived Azure login using GitHub OIDC.
5. Reads the existing app template and patches only the selected container image
   and a unique revision suffix. Environment variables, secret references,
   CPU/memory, scaling and health probes are preserved. App configuration/secrets
   are not copied into the request.
6. Waits for the intended new revision to become ready, then checks the public
   endpoint for healthy status, MongoDB connectivity and the exact running commit.
7. If verification fails, restores the previous immutable image and verifies
   health. If someone has changed the app separately, it stops instead of
   overwriting that change. A rollback leaves the workflow red for investigation.

Main deployments are serialized and are not cancelled by a subsequent push. Newer
pending pushes can replace an older pending run. Keep the app's 0–1 replica limit;
this change does not expand compute or change billing settings.

## Retiring Render

Render is a temporary rollback service, not a dependency of the Azure app. MongoDB,
Cloudflare R2 and Clerk are independent services and must remain.

After the first successful automatic Azure deployment, confirm signed-in history
and a real upload/analysis. Check the old `api.edaverse.app` hostname, which may
still point at Render; update its Azure custom-domain routing or retire that old
address deliberately. Then suspend the Render **web service** first. Once the
website is confirmed independent, delete the Render web service if desired.
Suspending provides a reversible transition; permanent deletion requires a final
user action/confirmation. Never delete the database, R2 bucket or Clerk application
as part of retiring this web service. The existing Render plan is free and does
not consume Azure credit.

## Disable or revoke

Set `AZURE_DEPLOY_ENABLED=false` to stop deployment while keeping image builds.
To revoke Azure access, remove this identity's app-scoped role assignment and
federated credential. Do not change the app's MongoDB/R2/Clerk credentials just
to disable deployment.

Sources:
- [GitHub OIDC in Azure](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect)
- [Azure app PATCH contract](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/container-apps/update?view=rest-resource-manager-containerapps-2025-07-01)
- [Azure custom roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/custom-roles)
