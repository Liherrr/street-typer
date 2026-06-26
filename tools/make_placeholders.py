#!/usr/bin/env python3
"""
Generate simple ANIMATED placeholder character frames (SVG) so the sprite engine runs before your
real filmed footage is ready. Two characters are produced under  characters/p1/  and  characters/p2/ ,
each with idle / attack1-4 / hurt / win / lose, plus a manifest.json.

>>> Replace these with YOUR frames: drop  idle_01.png, idle_02.png, ... attack1_01.png ...  into the
    character folder, then in that folder's manifest.json set  "ext": "png"  and the right "count"
    for each state. Filenames, states and the 2-digit numbering are the only contract. <<<

Run:  python tools/make_placeholders.py
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the fight/ folder
W, H = 300, 360
GROUND = 332


def _end(px, py, deg, length):
    r = math.radians(deg)
    return px + length * math.sin(r), py + length * math.cos(r)


def frame_svg(color, accent, label, idx, n, *, lean=0.0, yoff=0.0,
              armL=18.0, armR=18.0, legL=12.0, legR=12.0, lying=0.0, head_style="round"):
    cx = W / 2
    hip_y, neck_y, head_y, sh_y = 232 - yoff, 150 - yoff, 116 - yoff, 158 - yoff
    sx_l, sx_r, hx_l, hx_r = cx - 14, cx + 14, cx - 10, cx + 10
    hL, hR = _end(sx_l, sh_y, armL, 72), _end(sx_r, sh_y, armR, 72)
    fL, fR = _end(hx_l, hip_y, legL, 100), _end(hx_r, hip_y, legR, 100)

    def limb(x1, y1, x2, y2, w, c):
        return ('<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" '
                'stroke-width="%d" stroke-linecap="round"/>' % (x1, y1, x2, y2, c, w))

    if head_style == "square":   # blocky "robot/bruiser" head + antenna
        head = ('<rect x="%.0f" y="%.0f" width="44" height="44" rx="7" fill="%s"/>'
                '<line x1="%.0f" y1="%.0f" x2="%.0f" y2="%.0f" stroke="%s" stroke-width="4"/>'
                '<circle cx="%.0f" cy="%.0f" r="5" fill="%s"/>'
                % (cx - 22, head_y - 22, color, cx, head_y - 22, cx, head_y - 36, accent,
                   cx, head_y - 40, accent))
    else:                        # round "ninja" head + headband
        head = ('<circle cx="%.0f" cy="%.0f" r="26" fill="%s"/>'
                '<rect x="%.0f" y="%.0f" width="56" height="9" rx="3" fill="%s"/>'
                % (cx, head_y, color, cx - 28, head_y - 10, accent))
    parts = [
        limb(hx_l, hip_y, fL[0], fL[1], 13, color),
        limb(hx_r, hip_y, fR[0], fR[1], 13, color),
        limb(cx, neck_y, cx, hip_y, 16, color),
        limb(sx_l, sh_y, hL[0], hL[1], 11, color),
        limb(sx_r, sh_y, hR[0], hR[1], 11, accent),       # accent = the "weapon" arm
        head,
    ]
    if lying > 0:
        rot = ' transform="rotate(%.0f %.0f %.0f)"' % (lying * 88, cx, GROUND)
    elif lean:
        rot = ' transform="rotate(%.0f %.0f %.0f)"' % (lean, cx, hip_y)
    else:
        rot = ''
    dots = ''.join('<circle cx="%.0f" cy="350" r="3" fill="%s"/>' % (cx - (n - 1) * 6 + i * 12,
                   accent if i == idx else '#33445f') for i in range(n))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
            '<g%s>%s</g>'
            '<text x="%.0f" y="22" text-anchor="middle" font-family="monospace" font-size="13" '
            'fill="%s">%s</text>%s</svg>' % (W, H, W, H, rot, ''.join(parts), cx, accent, label, dots))


def states():
    """Per state: a list of pose dicts (one per frame)."""
    S = {}
    # intro/entrance: arms sweep from raised down into a fighting guard, then settles
    S['intro'] = [dict(armL=a, armR=a, yoff=y) for a, y in [(150, 7), (120, 4), (80, 1), (45, 0), (22, 0)]]
    S['idle'] = [dict(yoff=v, armL=16, armR=16) for v in (0, -3, -5, -3, 0, 2)]
    S['attack1'] = [dict(armR=a, lean=l) for a, l in [(20, 0), (70, 4), (108, 8), (95, 6), (45, 2)]]
    S['attack2'] = [dict(armR=a, armL=a * 0.7, lean=l) for a, l in [(18, 0), (60, 3), (102, 6), (82, 4), (30, 1)]]
    S['attack3'] = [dict(armR=a, lean=l) for a, l in [(20, 0), (-12, -2), (60, 4), (140, 9), (150, 6)]]
    S['attack4'] = [dict(legR=a, armL=-22, lean=l) for a, l in [(12, 0), (52, 2), (88, 5), (70, 3), (20, 0)]]
    S['hurt'] = [dict(lean=-12, armL=-30, armR=-30, yoff=2),
                 dict(lean=-19, armL=-42, armR=-42, yoff=4),
                 dict(lean=-8, armL=-20, armR=-20, yoff=1)]
    S['win'] = [dict(armL=145, armR=150, yoff=v) for v in (0, -4, -6, -2)]
    S['lose'] = [dict(lying=t, yoff=-8 * t) for t in (0.12, 0.42, 0.74, 1.0)]
    return S


LOOPS = {'idle', 'win'}
HOLDS = {'intro': 400}   # ms to linger on the final frame before settling to idle


def build_character(folder, name, color, accent, head_style="round"):
    out = os.path.join(ROOT, 'characters', folder)
    os.makedirs(out, exist_ok=True)
    st = states()
    manifest = {'name': name, 'fps': 10, 'ext': 'svg', 'states': {}}
    for state, poses in st.items():
        n = len(poses)
        for i, pose in enumerate(poses):
            svg = frame_svg(color, accent, '%s %s' % (name.upper(), state), i, n,
                            head_style=head_style, **pose)
            with open(os.path.join(out, '%s_%02d.svg' % (state, i + 1)), 'w', encoding='utf-8') as f:
                f.write(svg)
        entry = {'count': n}
        if state in LOOPS:
            entry['loop'] = True
        if state in HOLDS:
            entry['hold'] = HOLDS[state]
        manifest['states'][state] = entry
    with open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    return out, sum(len(p) for p in st.values())


def main():
    # two visibly DIFFERENT fighters (round head + headband vs square head + antenna), SF-warm colors
    a = build_character('p1', 'P1', '#ffd9a3', '#ff8a1e', head_style='round')
    b = build_character('p2', 'P2', '#ff7a3d', '#ffd23f', head_style='square')
    print('placeholders written:')
    print('  %s  (%d frames)' % a)
    print('  %s  (%d frames)' % b)
    print('replace the *.svg frames with your *.png frames and set ext:"png" + counts in manifest.json')


if __name__ == '__main__':
    main()
