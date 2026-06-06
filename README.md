<div align="center">

<br/>

<img src="https://placehold.co/72x72/0d1117/14b8a6?text=⬡&font=montserrat" alt="edaverse" width="72" height="72" style="border-radius:16px"/>

<h1>edaverse</h1>

<p><b>AI-powered Exploratory Data Analysis — no code required.</b><br/>
Upload a CSV or Excel file and get a complete analysis, cleaning report,<br/>and feature engineering suggestions in seconds.</p>

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Vite](https://img.shields.io/badge/Vite-latest-646cff?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![Recharts](https://img.shields.io/badge/Recharts-3-22b5bf?style=flat-square)](https://recharts.org)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6c47ff?style=flat-square&logo=clerk&logoColor=white)](https://clerk.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-primary-47a248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-14b8a6?style=flat-square)](LICENSE)

<br/>

[**Live Demo**](#) &nbsp;·&nbsp; [**Report a Bug**](../../issues) &nbsp;·&nbsp; [**Request a Feature**](../../issues)

<br/>

![edaverse Dashboard](https://placehold.co/1280x600/0d1117/14b8a6?text=edaverse+—+EDA+Workspace&font=montserrat)

<br/>

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Screenshots](#-screenshots)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Environment Variables](#environment-variables)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## Overview

**edaverse** is a full-stack EDA workspace that removes the friction from data analysis. Drop in any structured dataset and instantly get a streaming analysis covering profiling, distributions, correlations, outlier detection, and more — all without writing a single line of code.

**Why edaverse?**

- **Fast** — results stream in real time via Server-Sent Events, so you don't wait for a full analysis before seeing the first insight
- **Complete** — goes from raw file to cleaning report to feature-engineered export in one workflow
- **Smart** — AI narrative summarises the dataset and flags the most important findings
- **Safe** — Clerk JWT authentication, rate limiting, and atomic saves protect every request

---

## Features

<details>
<summary><b>📂 Upload & Parsing</b></summary>
<br/>

- Drag-and-drop or click-to-upload for **CSV** and **Excel (.xlsx / .xls)**
- Auto-detects file encoding — UTF-8, Latin-1, CP1252, and more
- Immediate schema inference with column types, null rates, and cardinality
- Configurable max upload size via environment variable

</details>

<details>
<summary><b>📊 Automated EDA — real-time streaming</b></summary>
<br/>

Analysis streams stage by stage so insights appear as they are computed:

| Stage | What you get |
|---|---|
| **Overview** | Row/column counts, null rate, encoding confidence, key observations |
| **Distributions** | Histogram + box plot for every numeric column |
| **Correlations** | Pearson & Spearman heatmap with column search and limit controls |
| **Target Analysis** | Feature–target relationships, mutual information scores |
| **Missingness** | Per-column null bars, missingness matrix, MNAR co-occurrence detection |
| **Skew & Outliers** | Skewed column list with severity bars, IQR outlier count per column |

A **7-step milestone tracker** in the top bar shows your analysis progress in real time.

</details>

<details>
<summary><b>🧹 Data Cleaning</b></summary>
<br/>

- Issues auto-detected and ranked as **Error / Warning / Info**
- Covers duplicates, nulls, constant columns, type mismatches, and outlier rows
- Select individual fixes or apply all with one click
- One-click **restore to original** — a backup is always kept
- Post-clean summary shows shape changes and a full fix log

</details>

<details>
<summary><b>⚙️ Feature Engineering</b></summary>
<br/>

Suggestions are grouped by category and can be applied selectively:

| Category | Examples |
|---|---|
| **Transforms** | Log, Box-Cox, square root for skewed columns |
| **Scaling** | StandardScaler, MinMax, RobustScaler |
| **Encoding** | One-hot, ordinal, target encoding |
| **Datetime** | Extract year / month / day / weekday / hour |
| **Binning** | Equal-width and quantile bins |
| **Missingness** | Indicator columns for MNAR patterns |
| **Time Series** | Lag features, rolling statistics |
| **Selection** | Drop near-zero-variance and high-null columns |

- **Target-aware encoding** — select a target column to unlock leakage-reduced target encoding for high-cardinality categoricals
- Before/after skewness and std preview on transform suggestions
- Apply selected operations and promote the result as the active dataset

</details>

<details>
<summary><b>🤖 AI Narrative</b></summary>
<br/>

- Generates a plain-English summary of the dataset after EDA completes
- Highlights key risks, dominant patterns, and recommended next steps
- Powered by a pluggable provider — OpenAI, Ollama, or any compatible API

</details>

<details>
<summary><b>🎯 UX & Onboarding</b></summary>
<br/>

- **Spotlight tour** — 7-step guided tour that points to each workspace area, just like production SaaS onboarding
- **Toast notifications** — configurable alerts for EDA complete, cleaning applied, and features engineered
- **Settings panel** — toggle notifications, set default correlation method, configure heatmap column limit, replay the tour
- **History panel** — browse and restore any previous dataset upload

</details>

<details>
<summary><b>🔒 Security & Observability</b></summary>
<br/>

- Clerk JWT authentication with JWKS signature verification in production
- Per-request correlation IDs (`X-Request-ID`) echoed on every response for tracing
- Rate limiting via SlowAPI
- Sentry error tracking on both frontend and backend
- EDA stream timeout via configurable `EDA_STREAM_TIMEOUT_SECS` deadline
- Atomic dataset save — metadata is never written if the file write fails
- Feature operation IDs validated on input (length + character checks)

</details>

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Recharts, Axios, React Dropzone |
| **Auth** | Clerk (JWT + JWKS) |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Data processing** | Pandas 2.2, PyArrow 16, SciPy, OpenPyXL |
| **Storage** | MongoDB (primary) + local Parquet / JSON (fallback) |
| **Object storage** | S3-compatible (Cloudflare R2 / AWS S3 via Boto3) |
| **Monitoring** | Sentry SDK, SlowAPI rate limiting |
| **Deployment** | DigitalOcean, Nginx, Systemd |

---

## Screenshots

| Upload | EDA Overview |
|---|---|
| ![Upload screen](https://placehold.co/760x420/0d1117/14b8a6?text=Drag+%26+Drop+Upload&font=montserrat) | ![EDA Overview](https://placehold.co/760x420/0d1117/14b8a6?text=EDA+Overview+%26+Stats&font=montserrat) |

| Correlation Heatmap | Cleaning Report |
|---|---|
| ![Correlations](https://placehold.co/760x420/0d1117/14b8a6?text=Correlation+Heatmap&font=montserrat) | ![Cleaning](https://placehold.co/760x420/0d1117/14b8a6?text=Cleaning+Report&font=montserrat) |

| Feature Engineering | Settings & Tour |
|---|---|
| ![Feature Engineering](https://placehold.co/760x420/0d1117/14b8a6?text=Feature+Engineering&font=montserrat) | ![Settings](https://placehold.co/760x420/0d1117/14b8a6?text=Settings+%26+Onboarding+Tour&font=montserrat) |

> Replace these placeholder images with real screenshots by adding them to a `docs/` folder in the repo and updating the paths above.

---

## Getting Started

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| MongoDB | Optional — falls back to local Parquet/JSON storage |

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend

# Copy and fill in environment variables
cp .env.example .env

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`.

---

### Environment Variables

<details>
<summary><b>Backend — <code>backend/.env</code></b></summary>
<br/>

```env
# Application
APP_ENV=development

# Auth
# In development, trust unverified JWTs (no Clerk signature check)
AUTH_TRUST_UNVERIFIED_JWT=true
TRUST_PROXY_AUTH_HEADERS=false

# In production, set these and set AUTH_TRUST_UNVERIFIED_JWT=false
# CLERK_ISSUER_URL=https://your-clerk-issuer.clerk.accounts.dev
# CLERK_JWKS_URL=https://your-clerk-issuer.clerk.accounts.dev/.well-known/jwks.json

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173

# MongoDB (optional — omit to use local file storage)
# MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname

# Cloudflare R2 / S3 object storage (optional)
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY_ID=
# R2_SECRET_ACCESS_KEY=
# R2_BUCKET=

# AI narrative provider (optional)
# OPENAI_API_KEY=sk-...
# OLLAMA_URL=http://localhost:11434

# Streaming
EDA_STREAM_TIMEOUT_SECS=300
```

</details>

<details>
<summary><b>Frontend — <code>frontend/.env</code></b></summary>
<br/>

```env
# Clerk publishable key (get from clerk.com dashboard)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here

# API base URL (leave empty to use same origin in production)
VITE_API_URL=http://localhost:8000

# App URL (used by Clerk for redirects)
VITE_APP_URL=http://localhost:5173

# Sentry DSN (optional)
VITE_SENTRY_DSN=
```

</details>

---

## Project Structure

```
dataflow/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, request-ID middleware
│   │   ├── routers/
│   │   │   ├── upload.py            # File upload & encoding detection
│   │   │   ├── eda.py               # Streaming EDA via SSE
│   │   │   ├── cleaning.py          # Issue detection & fix application
│   │   │   ├── features.py          # Feature engineering operations
│   │   │   ├── datasets.py          # Dataset CRUD & download
│   │   │   ├── ai.py                # AI narrative generation
│   │   │   └── demo.py              # Demo dataset endpoint
│   │   └── services/
│   │       ├── auth.py              # Clerk JWT verification
│   │       ├── store.py             # Dual-layer storage (Mongo + local)
│   │       ├── eda.py               # EDA computation engine
│   │       ├── cleaning.py          # Cleaning suggestion engine
│   │       ├── features.py          # Feature engineering engine
│   │       ├── parser.py            # CSV/Excel parsing & encoding detection
│   │       ├── limiter.py           # Rate limiting (SlowAPI)
│   │       └── object_storage.py    # S3-compatible upload/download
│   ├── tests/
│   │   ├── test_cleaning.py
│   │   └── test_parser.py
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Landing.jsx          # Marketing landing page
│       │   ├── Workspace.jsx        # Main workspace shell + settings panel
│       │   └── AuthPage.jsx         # Clerk auth flow
│       ├── components/
│       │   ├── WorkspaceResults.jsx # Tab router, EDA badge, milestone tracker
│       │   ├── WorkspaceTour.jsx    # SVG spotlight onboarding tour
│       │   ├── ToastContainer.jsx   # Stacked toast notifications
│       │   ├── AINarrative.jsx      # AI insight panel
│       │   ├── HistoryPanel.jsx     # Dataset history & restore
│       │   ├── Uploader.jsx         # Drag-and-drop uploader
│       │   └── tabs/
│       │       ├── OverviewTab.jsx
│       │       ├── DistributionsTab.jsx
│       │       ├── CorrelationsTab.jsx
│       │       ├── CleaningTab.jsx
│       │       ├── FeatureEngineeringTab.jsx
│       │       ├── TargetTab.jsx
│       │       └── StepsTab.jsx
│       └── services/
│           ├── api.js               # Axios client — retry, request IDs, auth headers
│           └── toast.js             # Toast events + localStorage settings
│
└── deploy/
    ├── setup.sh                     # One-command server provisioning
    ├── deploy.sh                    # Redeploy (git pull → build → restart)
    ├── nginx.conf                   # Reverse proxy configuration
    └── dataflow.service             # Systemd unit for auto-restart
```

---

## API Reference

<details>
<summary><b>All Endpoints</b></summary>
<br/>

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a CSV or Excel file |
| `GET` | `/api/datasets` | List all datasets for the current user |
| `GET` | `/api/datasets/{id}` | Get dataset metadata and schema |
| `DELETE` | `/api/datasets/{id}` | Delete a dataset and all its files |
| `GET` | `/api/datasets/{id}/eda` | **Stream EDA via SSE** |
| `GET` | `/api/datasets/{id}/suggestions` | Get ranked cleaning suggestions |
| `POST` | `/api/datasets/{id}/clean` | Apply selected cleaning fixes |
| `POST` | `/api/datasets/{id}/use-cleaned` | Promote cleaned file as active dataset |
| `POST` | `/api/datasets/{id}/restore-original` | Restore the original file |
| `GET` | `/api/datasets/{id}/download` | Download cleaned CSV |
| `GET` | `/api/datasets/{id}/feature-suggestions` | Get feature engineering suggestions |
| `POST` | `/api/datasets/{id}/engineer` | Apply selected feature operations |
| `POST` | `/api/datasets/{id}/use-engineered` | Promote engineered file as active dataset |
| `GET` | `/api/datasets/{id}/download-engineered` | Download engineered CSV |
| `POST` | `/api/ai/narrative` | Generate AI dataset narrative |
| `GET` | `/api/config` | Frontend runtime configuration |
| `GET` | `/health` | Service health — storage, dataset count, AI provider |

Every response includes an `X-Request-ID` header for end-to-end tracing.

</details>

<details>
<summary><b>SSE Stream Format — <code>GET /api/datasets/{id}/eda</code></b></summary>
<br/>

The EDA endpoint streams newline-delimited JSON events:

```
event: progress
data: {"stage": "distributions", "pct": 40}

event: result
data: {"stage": "correlation", "correlation": {...}, "correlation_spearman": {...}}

event: done
data: {"status": "complete"}
```

Stages in order: `overview` → `distributions` → `correlation` → `target` → `missingness` → `numeric_profile` → `categorical_profile` → `done`

</details>

---

## Deployment

### One-command setup on a fresh Ubuntu server

```bash
ssh root@your-server-ip

bash <(curl -fsSL https://raw.githubusercontent.com/23f1001130/dataflow/main/deploy/setup.sh)
```

This single script will:
1. Install Python 3, Node 20, Nginx, Git
2. Clone the repo to `/var/www/dataflow`
3. Create a Python virtual environment and install dependencies
4. Build the React frontend
5. Configure Nginx as a reverse proxy
6. Create and enable a Systemd service for auto-restart on reboot

### Redeploy after pushing changes

```bash
/var/www/dataflow/deploy/deploy.sh
```

### Production checklist

- [ ] Set `AUTH_TRUST_UNVERIFIED_JWT=false`
- [ ] Set `CLERK_ISSUER_URL` or `CLERK_JWKS_URL`
- [ ] Set `APP_ENV=production`
- [ ] Set `CORS_ALLOWED_ORIGINS=https://your-domain.com`
- [ ] Add your domain to Clerk's allowed origins and redirect URLs
- [ ] Install HTTPS: `certbot --nginx -d your-domain.com`
- [ ] Set `VITE_APP_URL=https://your-domain.com` before building the frontend

### Architecture on the server

```
Browser
  │
  ▼
Nginx :80/:443
  ├── /           → /var/www/html/dataflow/   (static React build)
  └── /api        → localhost:8000             (FastAPI via Uvicorn)
                         │
                    Systemd service
                    (auto-restarts on failure)
```

---

## Contributing

Contributions are welcome. To get started:

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/your-username/dataflow.git
cd dataflow

# 2. Create a feature branch
git checkout -b feat/your-feature-name

# 3. Make your changes

# 4. Run backend tests
cd backend && python -m pytest tests/

# 5. Push and open a Pull Request
git push origin feat/your-feature-name
```

**Guidelines**

- Keep PRs focused — one feature or bug fix per PR
- Match the existing code style (no linter is enforced, but be consistent)
- Add tests for new backend logic in `backend/tests/`
- Do not commit files from `backend/data/` — datasets are gitignored

---

## License

Distributed under the MIT License — see [`LICENSE`](LICENSE) for details.

---

<div align="center">

Made by [Aadil Iqbal](https://github.com/23f1001130)

</div>
