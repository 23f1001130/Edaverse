# Azure Container Apps backend

The frontend stays on Cloudflare Pages. The container exposes the existing FastAPI
backend on port **8000**, with health checks at `/health`.

## Image

Build locally with `docker build -f backend/Dockerfile -t edaverse-api .`. The Backend container
workflow builds and tests pull requests, then publishes tested main builds to
`ghcr.io/23f1001130/edaverse-api:latest` and an immutable `sha-<full-commit>` tag.
New GHCR packages default to private; the repository owner must make this
public-source image public in GitHub package settings before anonymous Azure pulls
work. No deployment secrets or runtime datasets are included in the image.

The image runs as UID/GID 10001 with `/app/data` writable for temporary dataset
files. A smoke test validates health, allowed-origin CORS, an uploaded CSV,
Parquet persistence and streamed EDA against the actual built container.

## Portal container page

| Field | Value |
| --- | --- |
| Use quickstart image | Unchecked |
| Name | `edaverse-api` |
| Image source | Docker Hub or other registries / Other registry |
| Registry server | `ghcr.io` |
| Image and tag | `23f1001130/edaverse-api:latest` (or the verified immutable tag) |
| Registry authentication | Anonymous, once public visibility is verified |
| Command / Arguments override | Empty; use the image's command |
| Development stack | None / Default |
| Workload profile | Consumption |
| GPU | None |
| CPU / Memory | 1 vCPU / 2 GiB |

Portal labels can vary; if image and tag are separate fields, enter
`23f1001130/edaverse-api` and `latest` separately.

## Required environment configuration

Copy existing deployment values directly from Render into Azure. Do not put secret
values into Git, chat, the Dockerfile or workflow. Use Azure Container App secrets
and secret references for credentials.

| Name | Value / purpose |
| --- | --- |
| `APP_ENV` | `production` (already the image default) |
| `AUTH_TRUST_UNVERIFIED_JWT` | `false` (already the image default) |
| `TRUST_PROXY_AUTH_HEADERS` | `false` (already the image default) |
| `CORS_ALLOWED_ORIGINS` | `https://edaverse.app` |
| `CLERK_ISSUER_URL` | Existing Clerk issuer, necessary for signed-in dataset ownership |
| `MONGODB_URI` | Existing connection, secret reference |
| `MONGODB_DB` / `MONGODB_COLLECTION` | Copy if set on Render, to use the same metadata collection |
| `R2_ACCOUNT_ID` | Existing account identifier |
| `R2_BUCKET` | Existing dataset bucket |
| `R2_ACCESS_KEY_ID` | Existing R2 credential, secret reference |
| `R2_SECRET_ACCESS_KEY` | Existing R2 credential, secret reference |
| `MAX_UPLOAD_MB` | `100` |
| `EDA_STREAM_TIMEOUT_SECS` | `300` |

Also copy custom R2 endpoint/prefix/region settings, anonymous TTL, AI-provider
settings and Sentry settings if present on the current backend. Do not create new
database/storage services just for this migration. Local container storage is a
cache; MongoDB and R2 remain the durable stores.

## Ingress, scaling and verification

- Enable external HTTP ingress with target port **8000** and HTTPS.
- Start with minimum **0**, maximum **1** replica, so local caches and admission
  control do not become inconsistent across multiple simultaneous replicas.
- Keep the Consumption workload profile; no dedicated/GPU profile is required.
- Use startup/readiness HTTP probes on `/health` with enough startup allowance.
- Configure credentials before importing private data. Confirm signed-in uploads
  retain the expected account ownership and history before changing live traffic.
- Test health/config, browser CORS, demo, a large workbook, dataset retrieval after
  restart (MongoDB/R2), and SSE completion using the Azure URL.
- Keep Render available while testing. Change Cloudflare's `VITE_API_URL` or the
  existing API DNS routing only after the Azure backend passes these checks.

The Consumption plan is usage-billed beyond free allowances; student credit is
finite. Scale-to-zero reduces idle compute cost but introduces cold starts. This
repository change only publishes the backend image; it does not provision Azure
resources or change production routing.
