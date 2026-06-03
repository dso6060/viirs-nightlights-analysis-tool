# Google Earth Engine (GEE) setup (optional)

This app can fetch VIIRS monthly radiance either from:

- **`VIIRS_SOURCE=noaa`** (default): downloads from NOAA EOG
- **`VIIRS_SOURCE=gee`**: reads from **Google Earth Engine** (`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`)

Use **GEE mode** if you want more stable small-area reductions (and/or you are preloading many places via `backend/preload_hotlist.py`).

---

## What you need (high level)

- **A Google Cloud project** you control
- **Earth Engine access enabled for that project** (project registration)
- **A service account + JSON key file** (local/dev convenience)  
  - For production on Google Cloud, prefer **Application Default Credentials (ADC)** instead of a key file.

---

## Step 1) Create a Google Cloud project

Create a new project in Google Cloud Console and note its **Project ID** (looks like `my-project-12345`).

You will use this as:

- `GEE_PROJECT_ID`
- the project passed to `ee.Initialize(..., project=...)`

---

## Step 2) Register the project for Earth Engine access

Earth Engine requires that the Cloud project be registered.

- Open the Earth Engine project registration flow:
  - `https://code.earthengine.google.com/register?project=YOUR_PROJECT_ID`
- Complete the registration for your intended usage type (commercial / non-commercial)

Reference: Earth Engine access guide (project registration):  
`https://developers.google.com/earth-engine/guides/access`

---

## Step 3) Enable the Earth Engine API

Ensure the **Earth Engine API** is enabled for the same Cloud project.

Reference: service accounts guide (Earth Engine API must be enabled):  
`https://developers.google.com/earth-engine/guides/service_account`

---

## Step 4) Create a service account + key (for local dev)

1. In Google Cloud Console:
   - **IAM & Admin → Service Accounts → Create service account**
2. Create a JSON key:
   - Open the service account → **Keys** → **Add key → Create new key → JSON**
   - Download the JSON key file and store it securely on your machine (do **not** commit it)

### Required IAM roles (typical)

Per the Earth Engine docs, when using a service account for computations (including REST-style calls),
grant the service account:

- **Earth Engine Resource Viewer**
- **Service Usage Consumer** (sometimes required depending on project config)

Reference (roles + guidance):  
`https://developers.google.com/earth-engine/guides/service_account#set_up_rest_api_access`

---

## Step 5) Configure environment variables for this repo

**Do not commit** `backend/.env`, service-account JSON files, or anything under `backend/.local-secrets/`.

### Option A — Your own GEE project (recommended for forks / new contributors)

Create `backend/.env` from `backend/.env.example`:

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your project ID and key path
```

```bash
export VIIRS_SOURCE=gee
export GEE_PROJECT_ID="YOUR_PROJECT_ID"
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/your-service-account-key.json"
```

### Option B — Friedso team local dev (existing production project)

If you maintain friedso production, copy the **service account JSON** from the server to a **gitignored** local path (example):

```bash
mkdir -p backend/.local-secrets
# From your machine (replace host if needed):
scp root@YOUR_SERVER:/etc/viirs/gee-viirs.json backend/.local-secrets/gee-viirs.json
chmod 600 backend/.local-secrets/gee-viirs.json
```

Set `GEE_PROJECT_ID` to the same value as `/etc/viirs/nightlights-prod.env` on the server (never paste the key or project into git).

Start the API from `backend/` so `backend/.env` is loaded (or export the same variables in your shell).

Notes:

- `GOOGLE_APPLICATION_CREDENTIALS` must point to the JSON file containing `client_email`.
- The backend initializes Earth Engine with:
  - `ee.ServiceAccountCredentials(client_email, GOOGLE_APPLICATION_CREDENTIALS)`
  - `ee.Initialize(..., project=GEE_PROJECT_ID)`

---

## Step 6) Install the Python dependency

GEE mode requires the Python Earth Engine client library:

- `earthengine-api`

It should already be present in `backend/requirements.txt`. If you see import errors for `ee`, re-install backend dependencies.

---

## Quick verification (recommended)

After setting env vars, start the backend and hit:

- `GET http://localhost:8000/`
- `GET http://localhost:8000/viirs/latest-available`

If initialization fails, the backend typically returns an error mentioning:

- missing `GEE_PROJECT_ID`
- missing `GOOGLE_APPLICATION_CREDENTIALS`
- permission / registration issues

