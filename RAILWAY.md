# Deploying to Railway

Railway runs containers, so both pieces deploy as services in one project from the same repo:

- **api** — the FastAPI backend (root `Dockerfile`)
- **web** — the React frontend served by nginx (`frontend/Dockerfile`)

Both Dockerfiles read `$PORT` (Railway injects it) and take config from env vars, so you never
rebuild to repoint the frontend at the backend.

> Prerequisite: push this repo to GitHub (Railway deploys from a repo or via its CLI).

---

## 1. Create the project + deploy the backend (`api`)

1. <https://railway.app> → **New Project → Deploy from GitHub repo** → pick this repo.
2. Railway detects the root `Dockerfile`. In the service settings:
   - **Root Directory:** `/` (repo root — the backend reads `agents/` and `schemas/` from here)
   - **Dockerfile Path:** `Dockerfile`
3. **Variables** (service → Variables):
   - `ANTHROPIC_API_KEY` = your key from <https://console.anthropic.com/>
   - `CORS_ORIGINS` = `*` for now (tighten in step 3)
   - *(optional)* `INTERPRETER_MODEL`, `ANALYST_MODEL`, … to pin models
   - Do **not** set `PORT` — Railway provides it.
4. **Settings → Networking → Generate Domain.** You get e.g.
   `https://cibmtr-api-production.up.railway.app`.
5. Verify: open `https://<api-domain>/health` → `{"status":"ok", ...}`.

## 2. Add the frontend service (`web`)

1. In the same project: **New → GitHub Repo → (same repo)** to add a second service.
2. Service settings:
   - **Root Directory:** `frontend`
   - **Dockerfile Path:** `frontend/Dockerfile` (Railway may show it as `Dockerfile` once the
     root dir is `frontend`)
3. **Variables:**
   - `API_BASE` = the backend domain from step 1 (e.g.
     `https://cibmtr-api-production.up.railway.app`) — this is injected into the app at start.
   - Leave `API_BASE` empty to run the frontend as a pure demo (bundled P-5297 example).
4. **Settings → Networking → Generate Domain.** That URL is your public app link.

## 3. Lock CORS down

Back on the **api** service, set `CORS_ORIGINS` to the `web` domain, e.g.
`https://cibmtr-web-production.up.railway.app`, and redeploy. Now only your frontend can call
the API from a browser.

Open the **web** domain — the catalog and runs now come from your backend.

---

## CLI alternative

```bash
npm i -g @railway/cli
railway login
railway init                       # creates/links a project

# backend
railway up                         # from repo root; uses ./Dockerfile
railway variables set ANTHROPIC_API_KEY=sk-... CORS_ORIGINS=*
railway domain                     # generate + print the api URL

# frontend (add a second service, then from frontend/)
cd frontend
railway up
railway variables set API_BASE=https://<your-api-domain>
railway domain
```

---

## What's live vs. still gated

The site, the study catalog, and the run flow go live immediately. A **reproduction run to
completion** still needs the hardened R sandbox (`infra/`, a stub today) and the T&C-gated
dataset the user downloads themselves. Until the sandbox image exists, starting a live run
reaches the R step and returns a clear "sandbox not configured" message (shown in the UI, not a
crash). The `examples/P-5297-synthetic` headless proof exercises the full spine without either
dependency.

> Adding R to the backend image (so runs can execute) is the next deploy step: extend the root
> `Dockerfile` with R + the `cibmtrrepro` package and a real `R_SANDBOX_CMD`, or run the sandbox
> as a third Railway service. See `docs/TODO.md` → "Sandbox hardening".

---

## Costs / safety for a public deployment

- The `api` service calls a **paid** API and (later) executes code — add rate limiting and a
  spend cap before sharing widely.
- Keep `RUNS_DIR` on the container's ephemeral disk for a demo; user data is session-scoped and
  purged regardless.
- The `ANTHROPIC_API_KEY` lives only in the backend service env, never in the frontend bundle.
