#!/usr/bin/env python3
"""
Turn raw filmed clips into game-ready Street Typer character frames.

For ONE character you give a folder of short clips, one per move, named by state:
    idle.mp4  attack1.mp4  attack2.mp4  attack3.mp4  attack4.mp4  hurt.mp4  win.mp4  lose.mp4
(any video extension works). This script, per clip:
  1. extracts frames with ffmpeg and picks a small, evenly-spaced set (the "step-print" choppy look),
  2. removes the background -> transparent PNG (AI matte by default; or chroma-key a green/blue screen),
  3. crops to the figure, scales every frame to ONE character height, and pastes it onto a fixed
     canvas with the FEET on a fixed baseline (so the fighter never jumps between frames/states),
  4. writes  characters/<char>/<state>_NN.png  + a matching manifest.json (ext:"png").

Then have me QA a few frames against the acceptance criteria in PROCESSING.md before committing.

Dependencies (build-time only; the GAME stays stdlib):
    - ffmpeg on PATH            (frame extraction)
    - pip install pillow numpy  (image ops)
    - pip install rembg         (AI background removal; first run downloads ~170 MB model)
Usage:
    python tools/process_clips.py RAW_DIR --char p1
    python tools/process_clips.py RAW_DIR --char p2 --matte green --key 00ff00
    python tools/process_clips.py RAW_DIR --char p1 --face left   # if you filmed facing left
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the fight/ folder

# default frame count + loop per state (override with --frames to scale all of them)
STATES = {"intro": (5, False), "idle": (6, True), "attack1": (5, False), "attack2": (5, False),
          "attack3": (5, False), "attack4": (5, False), "hurt": (3, False), "win": (4, True),
          "lose": (4, False)}
HOLDS = {"intro": 400}   # ms the intro/entrance pose lingers before settling to idle
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv", ".gif")


def die(msg):
    sys.exit("ERROR: " + msg)


def need(mod):
    try:
        return __import__(mod)
    except ImportError:
        die("missing '%s'. Install with:  pip install pillow numpy rembg" % mod)


def find_clip(raw, state):
    for ext in VIDEO_EXT:
        for cand in (os.path.join(raw, state + ext), os.path.join(raw, state.upper() + ext)):
            if os.path.isfile(cand):
                return cand
    hits = glob.glob(os.path.join(raw, state + ".*")) + glob.glob(os.path.join(raw, state + "_*.*"))
    return hits[0] if hits else None


def ffmpeg_exe():
    """Resolve an ffmpeg binary: prefer one on PATH, else fall back to the
    pip-installed imageio-ffmpeg bundle so the pipeline runs without a system ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        die("ffmpeg not found on PATH. Install it (https://ffmpeg.org/download.html) "
            "or run `pip install imageio-ffmpeg`, then re-run.")


def extract_frames(clip, tmp):
    out = os.path.join(tmp, "f_%05d.png")
    subprocess.run([ffmpeg_exe(), "-y", "-i", clip, "-vsync", "0", out, "-hide_banner", "-loglevel", "error"],
                   check=True)
    return sorted(glob.glob(os.path.join(tmp, "f_*.png")))


def pick_even(items, n):
    if len(items) <= n:
        return items
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]


_SESSION = None


def _rembg_session(model):
    """Create (once) and reuse a rembg session for the chosen model, so the
    ~170 MB net loads a single time and every frame is matted with the same model."""
    global _SESSION
    if _SESSION is None:
        from rembg import new_session
        _SESSION = new_session(model)
    return _SESSION


def _recover_red(rgba, rgb):
    """Union a saturated-red chroma key into the matte to rescue a red held object
    (e.g. P2's broom) that rembg drops when it is swung, motion-blurred, or raised
    against a bright wall. Red is unique in these clips (black costume, gray wall,
    brown floor are all excluded by the saturation gate), so this only adds the broom."""
    import cv2
    import numpy as np
    from PIL import Image
    arr = np.asarray(rgba).copy()
    src = np.asarray(rgb.convert("RGB"))
    hsv = cv2.cvtColor(src, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    rm = (((h <= 12) | (h >= 168)) & (s >= 110) & (v >= 60)).astype(np.uint8)
    # keep only sizable red components: this drops tiny floor/wall specks while preserving the
    # broom AND its motion-blur streak on fast swings (a morphological-open would erode the streak).
    n, lab, stats, _ = cv2.connectedComponentsWithStats(rm, 8)
    keep = np.zeros_like(rm)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= 40:
            keep[lab == i] = 1
    rm = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)  # solidify broom
    arr[..., 3][rm] = 255
    arr[..., :3][rm] = src[rm]
    return Image.fromarray(arr, "RGBA")


def matte(img, mode, key_hex, model="u2net", recover="none"):
    """Return an RGBA image with the background removed."""
    from PIL import Image
    import numpy as np
    img = img.convert("RGBA")
    if mode == "none":
        return img
    if mode == "green" or mode == "chroma":
        a = np.asarray(img).astype(np.int16)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        if key_hex:
            kr, kg, kb = int(key_hex[0:2], 16), int(key_hex[2:4], 16), int(key_hex[4:6], 16)
            dist = np.abs(r - kr) + np.abs(g - kg) + np.abs(b - kb)
            mask = dist < 120
        else:                                   # generic green-screen key
            mask = (g > r + 40) & (g > b + 40)
        out = a.copy()
        out[..., 3] = np.where(mask, 0, 255)
        out[mask, 1] = (out[mask, 0] + out[mask, 2]) // 2   # despill leftover green edges
        return Image.fromarray(out.astype("uint8"), "RGBA")
    # default: AI matte
    need("rembg")
    from rembg import remove
    out = remove(img, session=_rembg_session(model))
    if recover == "red":
        out = _recover_red(out, img)
    return out


def content_bbox(img):
    return img.split()[3].getbbox()    # bbox of non-transparent alpha


def _largest_component(mask):
    """Boolean mask of the largest connected alpha blob (the body), so a detached bit
    (e.g. a recovered weapon island) cannot pull the feet anchor or the height measure."""
    import numpy as np
    try:
        from scipy import ndimage
        lab, n = ndimage.label(mask)
        if n <= 1:
            return mask
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        return lab == (1 + int(np.argmax(sizes)))
    except Exception:
        return mask


def feet_anchor(fig):
    """Ground-contact anchor (x, y) of a cropped figure: x = horizontal centroid of the foot
    band, y = bottom of the body. Thin spikes (a downward weapon tip) and detached islands are
    ignored, so every frame can be planted by the SAME point and the fighter never drifts."""
    import numpy as np
    a = np.asarray(fig.split()[3]); H, W = a.shape
    body = _largest_component(a > 40)
    rc = body.sum(1); rows = np.where(rc > 0)[0]
    if not len(rows):
        return W / 2.0, float(H - 1)
    maxw = int(rc.max()); wthr = max(6, int(0.10 * maxw))
    fr = np.where(rc >= wthr)[0]
    feet_bot = int(fr[-1]) if len(fr) else int(rows[-1])
    band = max(4, int(0.06 * (rows[-1] - rows[0] + 1)))
    sub = body[max(0, feet_bot - band):feet_bot + 1, :]
    cc = sub.sum(0).astype(float)
    fx = float((np.arange(W) * cc).sum() / cc.sum()) if cc.sum() else W / 2.0
    return fx, float(feet_bot)


def body_height(fig):
    """Head-to-feet height of a cropped figure, excluding a thin raised weapon (via a width gate),
    so the scale can normalise the BODY to one size within and across characters."""
    import numpy as np
    a = np.asarray(fig.split()[3])
    body = _largest_component(a > 40)
    rc = body.sum(1); rows = np.where(rc > 0)[0]
    if not len(rows):
        return 0
    maxw = int(rc.max())
    head = np.where(rc >= max(18, int(0.25 * maxw)))[0]
    foot = np.where(rc >= max(6, int(0.10 * maxw)))[0]
    return int(foot[-1] - head[0]) if len(head) and len(foot) else int(rows[-1] - rows[0])


def process(raw, char, frames_override, canvas, char_h, baseline, mode, key_hex, face, fps, model="u2net",
            recover="none", picks_override=None, body_h=0.78, frame_mult=1):
    from PIL import Image
    import numpy as np
    picks_override = picks_override or {}
    cw, ch = canvas
    out_dir = os.path.join(ROOT, "characters", char)
    os.makedirs(out_dir, exist_ok=True)

    # ---- gather + matte every frame; record its cropped figure + ground-contact anchor ----
    plan, idle_bodies = [], []
    for state, (count, loop) in STATES.items():
        clip = find_clip(raw, state)
        if not clip:
            print("  (skip %-8s no clip found)" % state)
            continue
        n = (frames_override or count) * frame_mult
        with tempfile.TemporaryDirectory() as tmp:
            allframes = extract_frames(clip, tmp)
            if state in picks_override:                     # hand-picked frame indices for this state
                idxs = picks_override[state]
                picks = [allframes[min(max(i, 0), len(allframes) - 1)] for i in idxs]
            else:
                picks = pick_even(allframes, n)
            for i, fp in enumerate(picks):
                im = matte(Image.open(fp), mode, key_hex, model, recover)
                if face == "left":
                    im = im.transpose(Image.FLIP_LEFT_RIGHT)
                bb = content_bbox(im)
                if not bb:
                    continue
                fig = im.crop(bb)
                fx, fy = feet_anchor(fig)
                plan.append((state, i + 1, fig, fx, fy))
                if state == "idle":
                    idle_bodies.append(body_height(fig))
        print("  %-8s -> %d frames" % (state, n))

    if not plan:
        die("no usable frames produced — check the clip names and that the figure is visible.")

    # ---- ONE scale from the median IDLE body height (head->feet, weapon excluded). Driving the
    #      scale by body height (not the bbox, which the weapon inflates differently per fighter)
    #      makes the body a consistent size within AND across characters when both use --body-height.
    bodies = idle_bodies or [body_height(f) for _, _, f, _, _ in plan]
    ref_body = sorted(bodies)[len(bodies) // 2]
    scale = (ch * body_h) / ref_body
    base_y = int(ch * baseline)
    cx = cw / 2.0

    # ---- plant every frame by its FEET anchor at the SAME fixed point (centre x, baseline), so the
    #      fighter never drifts or floats; arms and weapons extend around the locked feet. ----
    counts = {}
    for state, idx, fig, fx, fy in plan:
        w, h = max(1, round(fig.width * scale)), max(1, round(fig.height * scale))
        fig_s = np.asarray(fig.resize((w, h), Image.LANCZOS))
        offx, offy = round(cx - fx * scale), round(base_y - fy * scale)
        canvas_arr = np.zeros((ch, cw, 4), np.uint8)
        dx0, dy0 = max(0, offx), max(0, offy)
        dx1, dy1 = min(cw, offx + w), min(ch, offy + h)
        if dx1 > dx0 and dy1 > dy0:                          # clip-safe copy (figure may overflow)
            sx0, sy0 = dx0 - offx, dy0 - offy
            canvas_arr[dy0:dy1, dx0:dx1] = fig_s[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]
        Image.fromarray(canvas_arr, "RGBA").save(os.path.join(out_dir, "%s_%02d.png" % (state, idx)))
        counts[state] = max(counts.get(state, 0), idx)

    # ---- manifest ----
    import json
    man = {"name": char.upper(), "fps": fps, "ext": "png", "states": {}}
    for state, (_, loop) in STATES.items():
        if state in counts:
            entry = {"count": counts[state]}
            if loop:
                entry["loop"] = True
            if state in HOLDS:
                entry["hold"] = HOLDS[state]
            man["states"][state] = entry
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)
    print("done -> %s  (%d frames). Now have the frames QA'd (see PROCESSING.md)." %
          (out_dir, len(plan)))


def main():
    ap = argparse.ArgumentParser(description="Process raw fighter clips into Street Typer frames.")
    ap.add_argument("raw_dir", help="folder with idle.* attack1.* ... win.* lose.* clips")
    ap.add_argument("--char", required=True, choices=["p1", "p2"], help="which character (Player 1 or 2)")
    ap.add_argument("--frames", type=int, default=0, help="override frames per state (0 = per-state defaults)")
    ap.add_argument("--frame-mult", type=int, default=1,
                    help="multiply every state's frame count (e.g. 5 = 5x smoother animation; remember to "
                         "raise --fps by the same factor to keep the same playback duration)")
    ap.add_argument("--canvas", default="640x540",
                    help="output canvas WxH (default 640x540; extra width gives a long weapon like "
                         "P2's broom room to swing around the feet-anchored body without clipping)")
    ap.add_argument("--char-height", type=float, default=0.82, help="(legacy; superseded by --body-height)")
    ap.add_argument("--body-height", type=float, default=0.78,
                    help="BODY height (head->feet, weapon excluded) as a fraction of the canvas. Use the "
                         "SAME value for both fighters so they come out the same size (default 0.78).")
    ap.add_argument("--baseline", type=float, default=0.96, help="feet position as fraction of canvas height")
    ap.add_argument("--matte", default="rembg", choices=["rembg", "green", "chroma", "none"])
    ap.add_argument("--rembg-model", default="u2net",
                    help="rembg model for --matte rembg (e.g. u2net, isnet-general-use, u2net_human_seg)")
    ap.add_argument("--recover", default="none", choices=["none", "red"],
                    help="rescue a held object the matte drops: 'red' chroma-keys a red weapon "
                         "(e.g. P2's broom) back into the cutout on swung/blurred frames")
    ap.add_argument("--picks", action="append", default=[],
                    help="override frame selection for a state when even sampling lands on a bad "
                         "frame, e.g. --picks attack2=0,14,33,44,57 (0-based indices into the "
                         "extracted frames; count must match the state's frame count)")
    ap.add_argument("--key", default="", help="chroma key color hex (e.g. 00ff00) for --matte green")
    ap.add_argument("--face", default="right", choices=["right", "left"], help="direction filmed (mirrored to face right)")
    ap.add_argument("--fps", type=int, default=10)
    a = ap.parse_args()
    if not os.path.isdir(a.raw_dir):
        die("raw_dir not found: " + a.raw_dir)
    cw, ch = (int(x) for x in a.canvas.lower().split("x"))
    picks_override = {}
    for spec in a.picks:
        st, _, idxs = spec.partition("=")
        picks_override[st.strip()] = [int(x) for x in idxs.split(",") if x.strip() != ""]
    print("processing %s from %s (matte=%s, model=%s, recover=%s, face=%s%s)" %
          (a.char, a.raw_dir, a.matte, a.rembg_model, a.recover, a.face,
           ", picks=" + str(picks_override) if picks_override else ""))
    process(a.raw_dir, a.char, a.frames, (cw, ch), a.char_height, a.baseline, a.matte, a.key, a.face, a.fps,
            a.rembg_model, a.recover, picks_override, a.body_height, a.frame_mult)


if __name__ == "__main__":
    main()
