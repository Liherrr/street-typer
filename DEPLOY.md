# Put Street Typer on a public URL (no firewall / VPN / same-network needed)

The game needs a tiny always-on server that relays the two players' moves in real time.
**Netlify can't run that** (it only serves static files + short serverless functions). Any
"web service" host works instead. The server is pure Python stdlib, so there's nothing to install.

Once deployed, **both players just open the same URL** — the first to load becomes Player 1,
the second becomes Player 2. Everything is outbound to the cloud, so no firewall/VPN/LAN issues.

---

## Step 0 — get this folder onto GitHub

This folder is already a git repo (`main` branch, one commit). Create an empty repo on GitHub
(no README/license — this folder has them), then from **inside this folder**:

```bash
git remote add origin https://github.com/<your-username>/street-typer.git
git push -u origin main
```

Or, with the GitHub CLI, one command does both create + push:

```bash
gh repo create street-typer --public --source=. --remote=origin --push
```

---

## Option 1 — Render (recommended, free)

One-click (after pushing — replace `YOUR-USERNAME` with your GitHub handle):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOUR-USERNAME/street-typer)

…or do it by hand:

1. Push this `fight/` folder to a **GitHub** repo (it can be the repo root or a subfolder).
2. Go to <https://render.com> and sign in (GitHub login is easiest).
3. **New +  ->  Web Service  ->** connect your repo.
4. Settings:
   - **Root Directory:** `fight`  *(only if fight/ is a subfolder; leave blank if it's the repo root)*
   - **Runtime:** Python 3
   - **Build Command:** *(leave blank)*
   - **Start Command:** `python fight_server.py --cloud`
   - **Instance Type:** Free
5. **Create Web Service** and wait ~1–2 min for the first deploy.
6. You get a URL like `https://street-typer.onrender.com`.
7. **Both players open that URL** → ready up → fight.

> Free-tier note: the service **sleeps after ~15 min idle**, so the *first* visit takes ~30–40 s
> to wake up (instant after that). Open the URL a minute before you start, or use the $7/mo plan
> for always-on. During a match there's constant traffic, so it never sleeps mid-game.

*(With the included `render.yaml`, you can instead do **New + -> Blueprint** and Render fills in
the settings automatically.)*

---

## Option 2 — No GitHub? Use Replit

1. <https://replit.com> → **Create Repl → Python**.
2. Upload **`fight_server.py`** and **`fight.html`** (both must be in the same folder).
3. Set the run command to: `python fight_server.py --cloud`
4. Press **Run** → Replit gives you a public URL.
5. Both players open it.

---

## Option 3 — Railway / Fly.io

Same idea: connect the repo, set the start command to `python fight_server.py --cloud`.
They set `$PORT` automatically, which the server reads.

---

## Heads-up: it's one shared arena

The hosted server runs **one match at a time** (first two visitors are P1/P2; a third sees
"arena full"). That's perfect for a grading session. If you ever need multiple simultaneous
matches, ask and I'll add room codes.
