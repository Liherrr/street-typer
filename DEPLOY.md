# Put Street Typer on a public URL (no firewall, VPN, or shared network needed)

The game needs a small always-on server that relays the two players' moves in real time. Netlify
cannot run that, since it only serves static files and short serverless functions. Any "web service"
host works instead. The server is pure Python standard library, so there is nothing to install.

Once it is deployed, both players open the same URL: the first to load becomes Player 1, the second
becomes Player 2. All traffic is outbound to the cloud, so there are no firewall, VPN, or LAN issues.

---

## Step 0: get this folder onto GitHub

This folder is already a git repo (`main` branch). Create an empty repo on GitHub (no README or
license, since this folder has them), then from inside this folder:

```bash
git remote add origin https://github.com/<your-username>/street-typer.git
git push -u origin main
```

Or, with the GitHub CLI, one command creates and pushes:

```bash
gh repo create street-typer --public --source=. --remote=origin --push
```

---

## Option 1: Render (recommended, free)

One-click, after pushing (replace `YOUR-USERNAME` with your GitHub handle):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOUR-USERNAME/street-typer)

Or do it by hand:

1. Push this folder to a GitHub repo (it can be the repo root or a subfolder).
2. Go to <https://render.com> and sign in (GitHub login is easiest).
3. New + -> Web Service -> connect your repo.
4. Settings:
   - Root Directory: leave blank if this folder is the repo root; set it to the subfolder name only if you nested it inside a larger repo
   - Runtime: Python 3
   - Build Command: leave blank
   - Start Command: `python fight_server.py --cloud`
   - Instance Type: Free
5. Create Web Service, then wait about 1 to 2 minutes for the first deploy.
6. You get a URL like `https://street-typer.onrender.com`.
7. Both players open that URL, ready up, and fight.

> Free-tier note: the service sleeps after about 15 minutes idle, so the first visit takes 30 to 40
> seconds to wake up (instant after that). Open the URL a minute before you start, or use the $7/month
> plan for always-on. During a match there is constant traffic, so it never sleeps mid-game.

With the included `render.yaml`, you can instead pick New + -> Blueprint and Render fills in the
settings automatically.

---

## Option 2: no GitHub? Use Replit

1. <https://replit.com> -> Create Repl -> Python.
2. Upload `fight_server.py` and `fight.html` (both in the same folder).
3. Set the run command to `python fight_server.py --cloud`.
4. Press Run, and Replit gives you a public URL.
5. Both players open it.

---

## Option 3: Railway or Fly.io

Same idea: connect the repo and set the start command to `python fight_server.py --cloud`. They set
`$PORT` automatically, which the server reads.

---

## One shared arena

The hosted server runs one match at a time: the first two visitors are P1 and P2, and a third sees
"arena full." That is fine for a single head-to-head session. If you ever need several matches at
once, ask and I will add room codes.
