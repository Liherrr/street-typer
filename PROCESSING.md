# Filming and processing your fighters into game frames

You film each fighter's moves, run them through `tools/process_clips.py`, and the result drops into
`characters/p1/` (Player 1) and `characters/p2/` (Player 2). Then send the processed frames back to me.
I check them against the acceptance criteria below before they go into the game.

> Who runs the processing? You or a separate agent can run `process_clips.py`; it is automated. I
> cannot ingest raw video in chat, so I do not process the footage myself. My job is the quality check
> before any frames go in.

---

## 1. How to film (so the cut-out and timing come out clean)

Each fighter needs 9 short clips, one per move:
`intro, idle, attack1, attack2, attack3, attack4, hurt, win, lose`. You can skip `hurt`, since there is
a flinch fallback, but it is worth filming.

For `intro`, film an entrance animation or a held starting pose. It plays once at the start of the round
(during the 3-2-1), then the fighter settles into `idle`, then "FIGHT!" begins. Start it from an off-pose
(walking in, standing up into stance, readying a weapon) and end on the fighting stance so it blends into
idle cleanly. A short held pose is fine; it lingers about 0.4 seconds before idle.

The rest:

- Background: a plain, evenly lit wall that contrasts with your clothes and skin (the AI matte handles
  this), or a green or blue screen if you have one (cleaner edges; use `--matte green`).
- Camera: locked off on a tripod, in the same position and zoom for every clip of a fighter. Do not move
  it between moves, since consistent framing is what keeps the frames aligned.
- Framing: full body, head to feet with a little headroom, feet near the bottom.
- Facing: face screen-right, toward the opponent. If you film facing left, pass `--face left`.
- Lighting: bright, even, and front-lit. Avoid casting a shadow on the background.
- Performance: do each move as distinct, held key poses (wind up, strike, recover). Crisp, slightly
  exaggerated poses read best at about 5 to 8 frames. Idle is a small loopable sway, win is a victory
  pose, and lose is a fall or slump.
- Costumes: film P1 and P2 in two different costumes so they read as two fighters.
- Length: keep clips short, 1 to 2 seconds each. The script samples evenly spaced frames from whatever
  you give it.

Name the files exactly: `idle.mp4`, `attack1.mp4`, through `lose.mp4` (any video extension), one folder
per fighter (for example `raw_p1/` and `raw_p2/`).

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

This writes `characters/p1/<state>_NN.png` plus `manifest.json` (and the same for p2). It extracts and
step-prints frames, removes the background to a transparent PNG, scales every frame to one BODY height
(head to feet, weapon excluded, so both fighters end up the same size when you pass the same
`--body-height`), and plants the detected feet on one fixed point (canvas centre, baseline) in every
frame so the fighter never drifts or floats. Arms and weapons extend around the locked feet.

Tunables: `--frames N` (frames per move), `--canvas 640x540` (wide so a long weapon can swing without
clipping), `--body-height 0.78` (body as a fraction of canvas height; use the SAME for both fighters),
`--baseline 0.96`. For a fighter whose held weapon is a saturated colour the matte keeps dropping on
fast/blurred frames, `--recover red` keys it back in; `--picks STATE=i,j,...` hand-picks frame indices
when even sampling lands on a bad frame.

---

## 3. Acceptance criteria (the QA gate; frames must pass these)

1. Clean transparent background. No colored halo or fringe around the figure, and no leftover background
   blobs. Green-screen edges should be despilled.
2. Consistent canvas. Every frame of every state is the exact same pixel size.
3. Grounded and stable. The figure's feet sit on the same baseline across all frames and states, and the
   character stays the same size throughout (no growing, shrinking, or vertical jump), except where a move
   deliberately crouches or leaps.
4. Centered and facing right. The figure is horizontally centered and faces screen-right (P2 is
   auto-mirrored).
5. Readable motion. Idle clearly loops, each attack reads as wind up, strike, recover, and win and lose
   are unmistakable. About 4 to 8 frames per move (choppy is good here; smooth is not the goal).
6. Counts match the manifest. The `count` per state in `manifest.json` equals the actual `state_NN.png`
   files, numbered from `01` with no gaps, and `ext` is `png`.
7. Lightweight. Each frame is no taller than the canvas (540 px by default) and reasonably small;
   the shipped frames run 60 to 90 KB each.

### Handing off for QA

Commit the processed `characters/p1` and `characters/p2` (or share one representative frame from each
state) and tell me. I will spot-check transparency, baseline alignment, sizing, facing, and counts, then
either green-light them or send back specific fixes (for example "attack3 frame 4 has a green halo" or
"lose frames sit 12 px above the baseline, raise `--baseline`"). Once they pass, they are already wired
into the game.
