# Filming & processing your fighters → game frames

You film each fighter's moves, run them through `tools/process_clips.py`, and the result drops into
`characters/p1/` (Player 1) and `characters/p2/` (Player 2). **Then send the processed frames back to
me — I QA them against the acceptance criteria below before they go in the game.**

> Who runs the processing? Either you or a separate agent can run `process_clips.py` — it's automated.
> I can't ingest raw video in chat, so I don't process the footage myself; **I own the quality gate.**

---

## 1. Film like this (so the cut-out and timing come out clean)

Each fighter needs **8 short clips**, one per move:
`idle, attack1, attack2, attack3, attack4, hurt, win, lose`. (You can skip `hurt` — there's a flinch
fallback — but it's worth filming.)

- **Background:** a plain, evenly-lit wall that **contrasts with your clothes/skin** (AI matte handles
  this) — or a **green/blue screen** if you have one (cleaner edges; use `--matte green`).
- **Camera:** locked off on a tripod, **same position/zoom for ALL clips of a fighter.** Don't move it
  between moves — consistency is everything.
- **Framing:** full body, head-to-feet in frame with a little headroom, **feet near the bottom.**
- **Facing:** face **screen-right** (toward the opponent). If you film facing left, pass `--face left`.
- **Lighting:** bright, even, front-lit. Avoid a shadow on the background.
- **Performance / step-print vibe:** do each move with **distinct, held key poses** (wind-up → strike →
  recover). Crisp, slightly exaggerated poses read best at ~5–8 frames. Idle = a small loopable sway.
  Win = a victory pose. Lose = take a fall / slump.
- **Costumes:** film P1 and P2 in your two different costumes so they're clearly two fighters.
- Keep clips short (1–2 s each); the script samples evenly-spaced frames from whatever you give it.

Name the files exactly: `idle.mp4`, `attack1.mp4`, … `lose.mp4` (any video extension), one folder per
fighter (e.g. `raw_p1/`, `raw_p2/`).

---

## 2. Process

```bash
pip install pillow numpy rembg          # one-time (rembg downloads a ~170 MB model on first run)
# ffmpeg must be on PATH: https://ffmpeg.org/download.html

python tools/process_clips.py raw_p1 --char p1
python tools/process_clips.py raw_p2 --char p2
# green screen instead of AI matte:   ... --matte green --key 00ff00
# filmed facing left:                 ... --face left
```

This writes `characters/p1/<state>_NN.png` + `manifest.json` (and same for p2). It already:
extracts + step-prints frames, removes the background to transparent PNG, scales every frame to one
character height, and **plants the feet on a fixed baseline** so the fighter never jumps.

Tunables: `--frames N` (frames per move), `--canvas 420x540`, `--char-height 0.82`, `--baseline 0.96`.

---

## 3. Acceptance criteria (my QA gate — frames must pass these)

1. **Clean transparent background** — no colored halo/fringe around the figure, no leftover background
   blobs. (Green-screen edges should be despilled.)
2. **Consistent canvas** — every frame of every state is the exact same pixel size.
3. **Grounded & stable** — the figure's **feet sit on the same baseline** across all frames and states;
   the character is the **same size** throughout (no growing/shrinking, no vertical jump) except where a
   move intentionally crouches/leaps.
4. **Centered & facing right** — figure horizontally centered; faces screen-right (P2 is auto-mirrored).
5. **Readable motion** — idle clearly loops; each attack reads as a wind-up→strike→recover; win/lose are
   unmistakable. ~4–8 frames per move (choppy is good; smooth is not the goal).
6. **Counts match manifest** — `manifest.json` `count` per state equals the actual `state_NN.png` files,
   numbered from `01` with no gaps; `ext` is `png`.
7. **Lightweight** — each frame ≤ ~512 px tall and reasonably small (a few hundred KB max).

### How to hand off for QA
Commit the processed `characters/p1` + `characters/p2` (or share a representative frame from each state),
and tell me. I'll spot-check frames (transparency, baseline alignment, sizing, facing, counts) and either
green-light them or send back specific fixes (e.g. "attack3 frame 4 has a green halo", "lose frames sit
12 px above the baseline — raise `--baseline`"). Once they pass, they're already wired into the game.
