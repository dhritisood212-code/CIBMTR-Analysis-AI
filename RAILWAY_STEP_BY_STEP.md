# Railway setup, step by step (for first-timers)

Your code is on GitHub. Now you'll turn it into two live websites on Railway:

- **api** — the "brain" (backend). Does the analysis work. Not meant to be looked at directly.
- **web** — the page people actually visit (frontend). Talks to `api` behind the scenes.

You'll do them in that order, because `web` needs to know `api`'s address.

Words you'll see, in plain English:

- **Project** — a container that holds your services. You already have one (it was called
  something like `remarkable-determination`).
- **Service** — one running program (one website). You'll have two: `api` and `web`.
- **Variables** — secret/config settings you type in (like your API key). The program reads
  them when it runs.
- **Deployment** — one attempt to build and run your code. Every time you change something,
  Railway makes a new deployment.
- **Domain** — the public web address (a `…up.railway.app` URL).
- **Staged changes / "Deploy" button** — Railway often holds your edits as "pending" and shows
  a purple **Deploy** button (or "Apply N changes"). Nothing goes live until you click it.

> Heads-up on cost: Railway's free trial has limited hours and may ask you to add a payment
> method or pick the Hobby plan (~$5/month) before it will deploy. That's normal.

---

## PART 1 — Get your Anthropic API key (needed in Part 2)

The backend needs a key to talk to Claude.

1. Go to <https://console.anthropic.com/> and sign in (or sign up).
2. Add a little billing credit so the key works: look for **Billing** or **Plans & Billing** in
   settings → add a card → buy a small amount (even $5 is plenty to test).
3. Go to **API Keys** → **Create Key**. Name it `cibmtr`.
4. It shows the key **once** — a long string starting with `sk-ant-…`. Click copy and paste it
   somewhere safe for a minute. You'll paste it into Railway in Part 2.

---

## PART 2 — Finish the backend service (`api`)

Open your Railway project. You should see a service card for **CIBMTR-Analysis-AI**. Click it to
open it. You'll see tabs across the top: **Deployments · Variables · Metrics · Settings**.

### 2.1 — Check the Settings tab
Click **Settings**. Scroll to the **Source** section:

- **Source Repo** should say `dhritisood212-code/CIBMTR-Analysis-AI`. Good.
- **Branch** should say `main`. The earlier red "Connected branch does not exist" message
  should be **gone** now (if it's still there, refresh the page, or click the branch box and
  pick `main`).
- **Root Directory** — leave this **empty / unset** for the backend. (Empty means "the top of
  the repo", which is where the backend's build file lives.) If you see a value in it, clear it.

Scroll to the **Build** section:

- Railway should show it's using a **Dockerfile**. You don't need to change anything — the file
  named `Dockerfile` at the top of your repo is the backend's recipe, and Railway finds it
  automatically. (If there's a "Dockerfile Path" box, it should be `Dockerfile`.)

You do **not** need to set a start command or a port — the app handles those itself.

### 2.2 — Add the variables
Click the **Variables** tab. For each one: click **New Variable** (or **+ New**), type the name,
type the value, confirm.

Add these two:

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | the `sk-ant-…` key from Part 1 |
| `CORS_ORIGINS` | `*` (just an asterisk — we tighten this in Part 4) |

Do **not** add a `PORT` variable — Railway sets that automatically.

> Tip: if there's a **Raw Editor**, you can paste both at once:
> ```
> ANTHROPIC_API_KEY=sk-ant-xxxxx
> CORS_ORIGINS=*
> ```

### 2.3 — Apply / Deploy
Look at the top of the screen. If you see a purple **Deploy** button or an **"Apply N changes"**
banner, click it. This tells Railway "take everything I just set and build it for real."

If you don't see that button, Railway may already be building (a change to variables usually
triggers a new deployment automatically).

### 2.4 — Watch it build
Click the **Deployments** tab, then click the newest deployment (top of the list). You'll see
**build logs** scrolling — Railway is downloading Python, installing the app, etc. This takes a
few minutes the first time.

- **Green "Success" / "Active"** = it built and is running. 
- **Red "Failed / Crashed"** = something went wrong. Copy the last ~20 lines of the log and send
  them to me; I'll tell you the fix.

### 2.5 — Give it a public address
Still in the service, go to **Settings → Networking** (sometimes under a "Public Networking"
heading) → click **Generate Domain**.

- If it asks for a **port**, it usually pre-fills the correct one — accept it. (If you must type
  one, the backend answers on the port Railway assigns, so the pre-filled value is right.)
- You'll get a URL like `https://cibmtr-analysis-ai-production.up.railway.app`. **Copy it** —
  this is your backend address; you'll need it in Part 3.

### 2.6 — Test the backend
Open a new browser tab and go to your backend URL with `/health` on the end, e.g.:

```
https://<your-backend-url>/health
```

You should see something like `{"status":"ok","anthropic_ready":true,...}`. If you see that,
the backend is live. 🎉 (Visiting the plain URL without `/health` may show a short "Not Found"
message — that's expected; there's no page at the root of the API.)

---

## PART 3 — Add the frontend service (`web`)

Now the part people actually visit. It lives in the **same repo**, in the `frontend` folder, so
you add it as a **second service** in the **same project**.

### 3.1 — Create the second service
1. Go back to the project canvas (the screen showing your service card). Click **+ New** (or
   **Create** / a **+** button), then choose **GitHub Repo**.
2. Pick **CIBMTR-Analysis-AI** again. A second service card appears. Open it.

### 3.2 — Point it at the `frontend` folder
Open the new service → **Settings → Source**:

- **Root Directory:** type `frontend` (this time you DO set it — it tells Railway to build the
  website part, which has its own recipe in the `frontend` folder).
- **Branch:** `main`.

Railway will use `frontend/Dockerfile` automatically once the root directory is `frontend`.

### 3.3 — Tell it where the backend is
Open the **Variables** tab of this `web` service and add:

| Name | Value |
|---|---|
| `API_BASE` | your backend URL from step 2.5, e.g. `https://cibmtr-analysis-ai-production.up.railway.app` |

(No trailing slash. If you leave `API_BASE` out entirely, the site still works but runs in a
self-contained **demo** mode showing the example study.)

### 3.4 — Deploy and get its address
1. Click **Deploy** / **Apply changes** if prompted, and watch the **Deployments** tab until
   it's green.
2. **Settings → Networking → Generate Domain.** This URL is **your public app link** — the one
   you share.

### 3.5 — Open your app
Click the `web` domain. You should see the CIBMTR Reproduction Panel, with the study catalog
loaded from your backend. 🎉

---

## PART 4 — Lock the door (CORS)

Right now the backend accepts requests from anywhere (`CORS_ORIGINS=*`). Point it at just your
site:

1. Open the **api** service → **Variables**.
2. Change `CORS_ORIGINS` from `*` to your `web` URL, e.g.
   `https://cibmtr-analysis-ai-web-production.up.railway.app` (no trailing slash).
3. Click **Deploy / Apply**. Railway redeploys the backend. Done.

---

## What will and won't work once it's live

- **Works:** the site loads, the study catalog, clicking into a study, the compliance screen,
  and the results viewer layout.
- **Won't finish yet:** actually *running a reproduction to completion*. That needs a piece we
  haven't built (a secure "R sandbox" that runs the statistics), plus the real dataset that
  users download from CIBMTR themselves. Until then, starting a run shows a clear message like
  "sandbox not configured" instead of finishing — it won't crash. That's the next build step
  whenever you're ready.

---

## If something goes wrong — quick fixes

- **Build fails immediately, mentions "Dockerfile not found":** for the `api` service the Root
  Directory must be empty; for the `web` service it must be `frontend`. Check Settings → Source.
- **Build fails in the `web` service during `npm`:** make sure its Root Directory is exactly
  `frontend` (lowercase, no slash).
- **Site loads but the catalog is empty / errors:** the `API_BASE` on the `web` service is
  probably wrong or has a trailing slash. Fix it and redeploy. Also confirm the backend
  `/health` works.
- **Browser console shows a "CORS" error:** set `CORS_ORIGINS` on the `api` service to your
  exact `web` URL (Part 4), or temporarily back to `*` to test.
- **"Application failed to respond":** the service built but isn't answering on the right port —
  usually a transient first-boot issue; open Deployments → Restart. If it persists, send me the
  deploy logs.
- **Anything red:** copy the last ~20 lines of the deploy log and send them to me.
