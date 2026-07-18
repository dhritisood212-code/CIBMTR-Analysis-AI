# Go live: GitHub → Anthropic key → Railway

An end-to-end walkthrough from the project folder on your computer to a public URL. Plan for
~20–30 minutes the first time. You need: this `cibmtr-repro/` folder, and free accounts on
GitHub, Anthropic Console, and Railway.

---

## Part 0 — One-time tool check

Open a terminal and confirm git is installed:

```bash
git --version        # any recent version is fine
```

If it prints a version, you're set. If not, install from <https://git-scm.com/downloads>.

---

## Part 1 — Get an Anthropic API key

1. Go to <https://console.anthropic.com/> and sign in (or create an account).
2. Add billing so the key can make calls: **Settings → Billing** (or **Plans & Billing**) →
   add a payment method and buy a small amount of credit (a few dollars is plenty to test).
3. Open **Settings → API Keys → Create Key**. Name it e.g. `cibmtr-repro`.
4. **Copy the key now** (it starts with `sk-ant-…`) and paste it somewhere safe — the console
   only shows it once. You'll paste it into Railway in Part 4, never into the code.

> Security: the key goes only into the backend's server environment on Railway. It is never in
> the frontend and must never be committed to GitHub. The repo's `.gitignore` already excludes
> `.env`, so a key placed there locally won't be pushed.

---

## Part 2 — Put the project on GitHub

### 2a. Create the repository on GitHub
1. Go to <https://github.com/new> (sign in / create account first).
2. Repository name: `CIBMTR-Analysis-AI` (already created).
3. Choose **Private** or Public.
4. **Do NOT** check "Add a README", ".gitignore", or "license" — the folder already has these.
5. Click **Create repository**. Leave the page open; you'll copy the URL in 2c.

### 2b. Initialise git in the project folder
In your terminal, `cd` into the project folder (the one containing `README.md`, `backend/`,
`frontend/`), then:

```bash
cd path/to/cibmtr-repro

git init
git add -A
git commit -m "CIBMTR Reproduction Panel: agents, orchestrator, R engine, frontend"
git branch -M main
```

> This commits source only — `node_modules/`, build output, `.env`, and run data are ignored by
> `.gitignore`, so nothing secret or bulky is included.

### 2c. Connect to GitHub and push
Connect the folder to your repo and push:

```bash
git remote add origin https://github.com/dhritisood212-code/CIBMTR-Analysis-AI.git
git push -u origin main
```

If prompted to authenticate, use your GitHub username and a **Personal Access Token** as the
password (GitHub → Settings → Developer settings → Personal access tokens → generate one with
`repo` scope), or install the GitHub CLI (`gh auth login`) which handles auth for you.

Refresh the GitHub page — your files should be there.

---

## Part 3 — Deploy the backend on Railway (`api` service)

1. Go to <https://railway.app> and sign in with GitHub.
2. **New Project → Deploy from GitHub repo** → authorise Railway to see your repos → pick
   `CIBMTR-Analysis-AI`.
3. Railway detects the root `Dockerfile` and starts building the backend. Open the service and
   go to **Settings**:
   - **Root Directory:** `/`
   - **Dockerfile Path:** `Dockerfile`
4. Go to **Variables** and add:

   | Variable | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | the `sk-ant-…` key from Part 1 |
   | `CORS_ORIGINS` | `*` (tighten in Part 5) |

   Do **not** add `PORT` — Railway sets it automatically.
5. **Settings → Networking → Generate Domain.** Copy the URL, e.g.
   `https://cibmtr-api-production.up.railway.app`.
6. Wait for the deploy to finish, then open `https://<api-domain>/health`. You should see
   `{"status":"ok", ...}`. (It's fine if `anthropic_ready` is true and there are no runs yet.)

---

## Part 4 — Deploy the frontend on Railway (`web` service)

1. In the **same** Railway project: **New → GitHub Repo →** pick `CIBMTR-Analysis-AI` again (this
   adds a second service from the same repo).
2. Open the new service → **Settings**:
   - **Root Directory:** `frontend`
   - **Dockerfile Path:** `frontend/Dockerfile` (Railway may display it as `Dockerfile` once the
     root directory is `frontend`)
3. **Variables** → add:

   | Variable | Value |
   |---|---|
   | `API_BASE` | the backend domain from Part 3, e.g. `https://cibmtr-api-production.up.railway.app` |

   (Leave `API_BASE` unset to run the frontend as a standalone demo with the bundled P-5297
   example.)
4. **Settings → Networking → Generate Domain.** **This URL is your public app link.**
5. Open it — you should see the CIBMTR Reproduction Panel, with the study catalog loaded from
   your backend.

---

## Part 5 — Lock down CORS

1. Go back to the **api** service → **Variables**.
2. Change `CORS_ORIGINS` from `*` to your `web` domain, e.g.
   `https://cibmtr-web-production.up.railway.app`.
3. Railway redeploys. Now only your frontend can call the API from a browser.

You're live. Share the **web** domain.

---

## What works now vs. what's still gated

- **Live now:** the site, the study catalog (from your backend), the compliance gate, the run
  flow, and the artifact viewer.
- **Not yet:** a reproduction run to *completion*. A live run drives the six-agent panel but the
  R-execution step needs the hardened R sandbox (`infra/`, a stub today) and the T&C-gated
  dataset the user downloads themselves. Until the sandbox image exists, starting a run reaches
  the R step and returns a clear "sandbox not configured" message in the UI — not a crash.
- The `examples/P-5297-synthetic` headless proof shows the full spine working without either
  dependency. Adding R to the backend image is the next step (`docs/TODO.md` → "Sandbox
  hardening").

## Pushing updates later

After changing code:

```bash
git add -A
git commit -m "describe your change"
git push
```

Railway auto-redeploys both services on every push to `main`.

## Cost & safety

- The `api` service calls a **paid** API. Set a spend limit in the Anthropic Console and add
  rate limiting before sharing the link widely.
- User-uploaded data is session-scoped and purged; only run artifacts persist. The API hosts no
  datasets and no secrets in the browser.
