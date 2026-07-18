# Deploying the CIBMTR Reproduction Panel

Two pieces: a **static frontend** (Netlify Drop) and a **backend API** (any Python/Docker host).
You can ship the frontend alone as a working demo in ~2 minutes, then add the backend to make
runs live.

---

## Step 1 — Put the frontend online (Netlify Drop, no account setup)

The frontend is already built. You have two equivalent options:

**A. Drop the zip.** Go to <https://app.netlify.com/drop> and drag
`frontend/cibmtr-repro-frontend-site.zip` onto the page. Netlify unzips and gives you a public
URL like `https://<random-name>.netlify.app`.

**B. Drop the folder.** Drag the `frontend/site/` folder onto the same page.

That's it — the site is live. With no backend configured it runs in **demo mode**: it renders
the real P-5297 example (catalog → compliance gate → run flow → color-coded match report → the
`reproduce_P-5297.R` script → bundle). Anyone can open it; no API key, no server, no cost.

> To rebuild after code changes: `cd frontend && npm install && npm run build -- --outDir site`,
> then re-drop `site/`.

---

## Step 2 — Deploy the backend API (to make runs live)

The backend is a FastAPI app; a `Dockerfile` and `render.yaml` are included. **Render** is the
simplest, but any Docker host (Railway, Fly.io, Cloud Run) works.

**Render (Blueprint):**
1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → select the repo. It reads `render.yaml`.
3. Set the `ANTHROPIC_API_KEY` secret in the dashboard (from
   <https://console.anthropic.com/>). Don't commit it.
4. Deploy. You get a URL like `https://cibmtr-repro-api.onrender.com`. Check
   `https://<that-url>/health` — it should return `"status":"ok"`.

**Any Docker host (manual):**
```bash
docker build -t cibmtr-repro-api .          # build context = repo root
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sk-... cibmtr-repro-api
```

---

## Step 3 — Point the frontend at the backend (no rebuild)

Edit **`config.js`** inside the deployed site and set your backend URL:

```js
window.__APP_CONFIG__ = { apiBase: "https://cibmtr-repro-api.onrender.com" };
```

- On Netlify: Site → **Deploys** → drag a new `site/` folder whose `config.js` has the URL, or
  edit the file and redeploy. (Because it's runtime config, you don't rebuild the bundle.)
- Then tighten CORS: set `CORS_ORIGINS=https://<your-site>.netlify.app` on the backend.

Reload the site — the catalog and runs now come from your backend instead of the demo fixtures.

---

## What works live vs. what's still gated

| Live now | Needs more work (see `docs/TODO.md`) |
|---|---|
| Frontend (all screens), demo mode, study catalog from the API, run flow, compliance gate, artifact viewer | A **real reproduction run** to completion |

A live run drives the six-agent panel, but the R execution step needs the **hardened R sandbox**
(`infra/`, currently a stub) and the **T&C-gated dataset** (users download it themselves). Until
the sandbox image exists, starting a run reaches the R step and returns a clear
"sandbox not configured" message — surfaced in the UI, not a crash. The `examples/P-5297-synthetic`
headless proof shows the full spine working end-to-end without either dependency.

---

## Security / compliance notes for a public deployment

- The API hosts **no datasets** and **no secrets in the client**; the Anthropic key lives only
  in the backend's server environment.
- User-uploaded data is session-scoped and purged; only run artifacts persist. Keep the backend's
  `RUNS_DIR` on ephemeral storage for a public demo.
- `CORS_ORIGINS=*` is fine for a keyless public demo API; restrict it to your site once the
  backend does real work.
- Rate-limit the backend before opening it widely — it executes code and calls a paid API.
