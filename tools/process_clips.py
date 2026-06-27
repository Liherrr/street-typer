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


def matte(img, mode, key_hex, model="u2net"):
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
    return remove(img, session=_rembg_session(model))


def content_bbox(img):
    return img.split()[3].getbbox()    # bbox of non-transparent alpha


def process(raw, char, frames_override, canvas, char_h, baseline, mode, key_hex, face, fps, model="u2net"):
    from PIL import Image
    cw, ch = canvas
    out_dir = os.path.join(ROOT, "characters", char)
    os.makedirs(out_dir, exist_ok=True)

    # ---- gather + matte every frame we want, remember its cropped figure ----
    plan, idle_heights = [], []
    for state, (count, loop) in STATES.items():
        clip = find_clip(raw, state)
        if not clip:
            print("  (skip %-8s no clip found)" % state)
            continue
        n = frames_override or count
        with tempfile.TemporaryDirectory() as tmp:
            picks = pick_even(extract_frames(clip, tmp), n)
            for i, fp in enumerate(picks):
                im = matte(Image.open(fp), mode, key_hex, model)
                if face == "left":
                    im = im.transpose(Image.FLIP_LEFT_RIGHT)
                bb = content_bbox(im)
                if not bb:
                    continue
                fig = im.crop(bb)
                plan.append((state, i + 1, fig))
                if state == "idle":
                    idle_heights.append(fig.height)
        print("  %-8s -> %d frames" % (state, n))

    if not plan:
        die("no usable frames produced — check the clip names and that the figure is visible.")

    # ---- one scale for ALL frames so the fighter is a consistent size; feet on the baseline ----
    ref_h = sorted(idle_heights)[len(idle_heights) // 2] if idle_heights else \
        sorted(f.height for _, _, f in plan)[len(plan) // 2]
    scale = (ch * char_h) / ref_h
    base_y = int(ch * baseline)

    # Keep the fighter at full size, but don't let an extreme outlier pose (e.g. a victory weapon
    # raise that towers over the idle height) get clipped at the top: cap the scale so the
    # 92nd-percentile-tall frame still fits under a small top margin. This leaves the normal
    # standing/attack frames untouched and only reins in a rare hero pose. Feet stay on baseline.
    import math
    top_margin = max(2, int(ch * 0.012))
    hs = sorted(f.height for _, _, f in plan)
    p92 = hs[min(len(hs) - 1, int(math.ceil(0.92 * len(hs))) - 1)]
    fit_scale = (base_y - top_margin) / p92
    if fit_scale < scale:
        print("  (scale capped %.3f -> %.3f so tall poses aren't clipped at the top)" % (scale, fit_scale))
        scale = fit_scale

    counts = {}
    for state, idx, fig in plan:
        w, h = max(1, round(fig.width * scale)), max(1, round(fig.height * scale))
        fig = fig.resize((w, h), Image.LANCZOS)
        canvas_img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas_img.alpha_composite(fig, ((cw - w) // 2, base_y - h))   # centered x, feet at baseline
        canvas_img.save(os.path.join(out_dir, "%s_%02d.png" % (state, idx)))
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
    ap.add_argument("--canvas", default="420x540", help="output canvas WxH (default 420x540)")
    ap.add_argument("--char-height", type=float, default=0.82, help="figure height as fraction of canvas")
    ap.add_argument("--baseline", type=float, default=0.96, help="feet position as fraction of canvas height")
    ap.add_argument("--matte", default="rembg", choices=["rembg", "green", "chroma", "none"])
    ap.add_argument("--rembg-model", default="u2net",
                    help="rembg model for --matte rembg (e.g. u2net, isnet-general-use, u2net_human_seg)")
    ap.add_argument("--key", default="", help="chroma key color hex (e.g. 00ff00) for --matte green")
    ap.add_argument("--face", default="right", choices=["right", "left"], help="direction filmed (mirrored to face right)")
    ap.add_argument("--fps", type=int, default=10)
    a = ap.parse_args()
    if not os.path.isdir(a.raw_dir):
        die("raw_dir not found: " + a.raw_dir)
    cw, ch = (int(x) for x in a.canvas.lower().split("x"))
    print("processing %s from %s (matte=%s, model=%s, face=%s)" % (a.char, a.raw_dir, a.matte, a.rembg_model, a.face))
    process(a.raw_dir, a.char, a.frames, (cw, ch), a.char_height, a.baseline, a.matte, a.key, a.face, a.fps,
            a.rembg_model)


if __name__ == "__main__":
    main()
