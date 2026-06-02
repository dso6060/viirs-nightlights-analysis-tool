# Server deployment (clean import + safe ops)

This repo is designed to run as:

- **Frontend**: static files served by **nginx**
- **Backend**: **FastAPI** served by **uvicorn** (recommended under **systemd**)
- **Cache/DB**: SQLite file used as a cache + query logs (path via `VIIRS_DB_PATH`)

This document assumes you will **copy a prepared bundle** into a local repo on your server-side machine, then deploy from that local repo to the server.

---

## What to copy (bundle contents)

Minimum required:

- `backend/` (Python API)
- `frontend/` (static UI)
- `nginx.conf` (reference config; you’ll install a server-specific variant)
- `scripts/build_hotlist.py` (generates `backend/data/hotlist.json`)
- `backend/data/clusters.json`
- `backend/requirements.txt`

Recommended but environment-specific:

- `systemd/viirs-backend.service` (template provided in bundle)
- `nginx/viirs.conf` (template provided in bundle)
- `.env.example` (template provided in bundle)

Do **not** copy:

- `.git/`, `.cursor/`, `.pytest_cache/`, `__pycache__/`
- `*.db`, `*.sqlite*` unless you *intentionally* want to ship a warmed cache DB
- `.DS_Store`, logs, temp folders

---

## Environment variables (backend)

Create a `.env` file (or set systemd `Environment=` lines) with:

- **`CORS_ORIGINS`**: comma-separated allowed origins (do not use `*` in prod)
  - example: `https://yourdomain.com`
- **`VIIRS_DB_PATH`**: path to SQLite cache DB
  - example: `/var/lib/viirs/cache/viirs_cache_prod.db`
- **`VIIRS_HOTLIST_PATH`**: where `hotlist.json` lives
  - example: `/srv/viirs/app/backend/data/hotlist.json`
- **`VIIRS_CLUSTERS_PATH`**: where `clusters.json` lives
  - example: `/srv/viirs/app/backend/data/clusters.json`
- **`VIIRS_SOURCE`**: `noaa` (default) or `gee`
  - if `gee`, you must set **`GEE_PROJECT_ID`**
- **`NOAA_EOG_USERNAME`**, **`NOAA_EOG_PASSWORD`**: optional (only if you use NOAA auth)
- **Overload guards** (already supported by the code):
  - `MAX_INFLIGHT_NETWORK` (default 4)
  - `RATE_LIMIT_PER_MIN` (default 60)
  - `MIN_CF_CVG` (default 5)

---

## Staging vs production cache DB: separate or shared?

### Recommendation: **separate** cache DBs

Use separate SQLite DB files (or separate Redis DBs if you later move off SQLite):

- **Prod**: `/var/lib/viirs/cache/viirs_cache_prod.db`
- **Staging**: `/var/lib/viirs/cache/viirs_cache_staging.db`

Reasons:

- **Safety**: staging traffic and experiments don’t pollute production cache/logs.
- **Performance isolation**: staging load spikes won’t lock/contend the prod DB file.
- **Data integrity**: staging can change schema/behavior without risking prod.
- **Debugging**: query logs stay environment-specific (very useful operationally).

### When a shared cache can be acceptable

Only if staging is truly low-traffic, identical code/config, and you treat staging as read-only.
Even then, it’s usually not worth the risk—SQLite file locking makes contention easy to hit.

---

## Making deployments clean and smooth

### Use an “atomic” deploy layout

On the server, deploy into versioned directories and switch a symlink:

- `/srv/viirs/releases/2026-05-29_1610/`  (new)
- `/srv/viirs/current -> /srv/viirs/releases/2026-05-29_1610/`

Benefits:

- Easy rollback: repoint symlink to previous release.
- Zero partial state: you never run half-copied code.

### Separate **code** from **state**

Keep runtime state outside the repo checkout:

- SQLite cache DB: `/var/lib/viirs/cache/`
- Logs: `/var/log/viirs/`
- Temp downloads (if any): `/var/cache/viirs/`

This prevents “rm -rf release” from deleting your cache/logs and avoids filling up your code disk.

---

## Capacity + safety guardrails (so the server doesn’t fall over)

### Compute / CPU

- Run uvicorn with **controlled workers** (start with 1–2 on small VPS).
- Keep `MAX_INFLIGHT_NETWORK` conservative; NOAA/OSM calls can stall and tie up workers.

If you run behind nginx, you can scale by:

- increasing uvicorn workers (CPU-bound work benefits; network-bound work often doesn’t)
- tightening timeouts (so hung upstream calls don’t pile up)

### Memory

Typical failure mode: many concurrent requests causing large in-memory responses + python overhead.

Mitigations already present in code:

- `MAX_INFLIGHT_NETWORK` semaphore limits concurrent upstream calls
- `RATE_LIMIT_PER_MIN` slows abusive clients

Add OS-level guardrails:

- systemd `MemoryMax=` for backend service
- configure swap (small VPS) to avoid OOM-killer thrash

### Storage

Primary risk: cache DB growth + logs.

Mitigations:

- Put the SQLite DB under `/var/lib/viirs/cache/` on a volume with room.
- Rotate logs (journald already rotates; add nginx logrotate if needed).
- Optional: periodically prune `query_logs` if you don’t need long retention.

### Traffic / bandwidth

NOAA downloads can be large.

Mitigations:

- nginx `proxy_read_timeout` set (already in `nginx.conf` reference)
- keep concurrency low to avoid saturating outbound bandwidth
- consider a CDN for static frontend assets (optional)

---

## nginx + systemd (reference templates)

Use the bundle templates:

- `nginx/viirs.conf`: serves `frontend/` and proxies `/api/` to backend
- `systemd/viirs-backend.service`: runs uvicorn, restarts on failure, applies resource limits

After installing:

```bash
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl daemon-reload
sudo systemctl enable viirs-backend
sudo systemctl restart viirs-backend
```

---

## First boot checklist

- Generate hotlist once (creates `backend/data/hotlist.json`):
  - `python3 scripts/build_hotlist.py`
- Confirm backend health:
  - `curl -fsS http://127.0.0.1:8000/ | jq .name` (or just curl without jq)
- Confirm nginx routing:
  - `curl -I http://yourdomain/`
  - `curl -I http://yourdomain/api/`

