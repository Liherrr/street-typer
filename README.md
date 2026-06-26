# Street Typer

A **live, two-player typing fight.** Both players type a stream of random letters; every clean
**4-letter block** throws an attack at the opponent. Damage = the *information* you transmit, so the
fight is literally a race to out-type your rival. Wrapped in a Mortal-Kombat-style brawl with
custom, swappable fighters.

It's also an honest **bit-rate instrument**: each selection is i.i.d. uniform over `N = 26` letters,
and the end screen reports both players' achieved bit rate
`B = log2(N-1) × max(Sc − Si, 0) / t`.

- **HP = 1200 = 20 bits/sec × 60 s** — only a ~20 bps run can K.O. the opponent in a 60-second round.
- **No dependencies.** Pure Python standard library on the server; the game is a single HTML page.
- **Plays anywhere.** Host locally on a LAN, or deploy to a free URL both players just open.

---

## Play it

### Option A — one shared URL (no firewall / VPN / same-network hassle)
Deploy to any "web service" host (Render's free tier is easiest) and both players open the URL —
first to load is **Player 1**, second is **Player 2**. See **[DEPLOY.md](DEPLOY.md)**.

```
Start command:  python fight_server.py --cloud
```

### Option B — local, on your own network
- **Windows:** double-click **`Street Typer.cmd`** (it opens the firewall once, with a Yes prompt).
- **macOS:** double-click **`Street Typer.command`** (first time: right-click → Open).
- Or from a terminal: `python fight_server.py`

The first machine to launch becomes the host; the second auto-discovers it on the LAN (or opens the
URL shown on the host screen). Then both press **Ready** → 3-2-1 → fight.

---

## How it works

| | |
|---|---|
| **Alphabet** | `N = 26` letters, drawn i.i.d. uniform with replacement (no language model / patterns) |
| **Attack** | every completed 4-letter block; damage = `log2(25) × (correct − wrong)` bits |
| **HP** | `1200` = `20 bps × 60 s`, so a clean ~20 bps run is exactly lethal |
| **Win** | first to drop the opponent to 0, or higher HP at the 60-second buzzer |
| **Score** | the end screen reports each player's `B`, `Sc`, `Si` — a real measurement, not just a game |

The server is the authoritative referee (HP, score, winner); browsers send keystroke results and
render the fight. Reconnects reclaim the same player slot (per-tab token), so a network blip can't
lock anyone out.

---

## Custom fighters (the Mortal Kombat part)

Each character is a folder of **transparent frame images** plus a `manifest.json`. Drop your own
filmed, step-printed frames in and they appear automatically — no code changes.

```
characters/p1/                 # Player 1's character     (p2/ = Player 2's)
  intro_01.png … intro_05.png  # entrance: plays once at round start, then settles to idle
  idle_01.png … idle_06.png    # loops
  attack1_01.png … attack1_05.png
  attack2_…  attack3_…  attack4_…   # your 3–4 attacks (cycled per 4-block)
  hurt_01.png … hurt_03.png    # plays when hit (optional; else a flinch)
  win_01.png …                 # victory (loops/holds)
  lose_01.png …                # K.O.
  manifest.json
```

`manifest.json` just declares the frame count per state:

```json
{
  "name": "Ninja", "fps": 10, "ext": "png",
  "states": {
    "intro":  { "count": 5, "hold": 400 },
    "idle":   { "count": 6, "loop": true },
    "attack1":{ "count": 5 }, "attack2": { "count": 5 },
    "attack3":{ "count": 5 }, "attack4": { "count": 5 },
    "hurt":   { "count": 3 },
    "win":    { "count": 4, "loop": true }, "lose": { "count": 4 }
  }
}
```

**Filming tips:** transparent background (green-screen/cut-out), consistent canvas + feet on a fixed
baseline, face **right** (Player 2 is auto-mirrored), keep frame counts low (~4–8) for the choppy
digitized cadence, and keep frames ≤ ~512 px tall.

The repo ships **animated placeholder fighters** so it runs immediately; regenerate them anytime with
`python tools/make_placeholders.py`. If a character's assets are missing, the game falls back to the
emoji fighters.

---

## Files

| file | role |
|---|---|
| `fight_server.py` | relay + referee (pure stdlib); serves the page, HP/score, lobby, 60-s round |
| `fight.html` | the whole game (typing, combat, sprite engine, FX) |
| `characters/p1`, `characters/p2` | the two fighters' frames + manifest (replace with your footage) |
| `tools/make_placeholders.py` | regenerates the placeholder fighters |
| `Street Typer.cmd` / `.command` | double-click launchers (Windows / macOS) |
| `Allow Firewall (run as admin).cmd` | one-click Windows firewall opener (local play) |
| `render.yaml`, `Procfile`, `requirements.txt` | cloud deploy config |
| `DEPLOY.md` | step-by-step hosting guide |

## License

MIT — see [LICENSE](LICENSE).
