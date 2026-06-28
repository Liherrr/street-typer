#!/usr/bin/env python3
"""
Street Typer - a two-PC LIVE typing fight.  Pure Python standard library: no pip installs,
no model, no microphone.  Typing is exact in the browser, so this process is only a tiny relay +
referee between the two players' browsers.

How two testers connect with zero fuss:
  - Each runs: python fight_server.py
  - The FIRST instance becomes the HOST (starts the web server + a UDP discovery responder).
  - The SECOND instance broadcasts on the LAN, finds the host automatically, and just opens the
    fight in its browser -- no IP typing.
  - Fallback if the network blocks UDP discovery: the host screen shows a join URL + QR code; the
    other player opens that URL.

Referee rules (server is authoritative):
  - N = 26 letters, i.i.d. uniform.  Each completed 4-letter block fires an attack (correct or not).
  - damage = log2(N-1) * (correct - wrong) accumulated; an opponent's HP = HP_MAX - your best
    cumulative bit-score.  HP_MAX = 20 bps * 60 s = 1200 bit-damage, so ONLY a ~20 bps run can KO.
  - First to drop the opponent to 0 wins; at 60 s the higher remaining HP wins.

Endpoints:
  GET  /                 -> fight.html
  GET  /sync             -> SSE stream; assigns this browser a player slot, relays opponent events
  POST /event            -> {pid, t, ...}  player actions (ready / attack / rematch / quit)
  GET  /lan              -> {url, ip, port}  the join URL for the host screen
"""
import argparse
import json
import math
import os
import queue
import random
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = str(int(time.time()))          # per-process token; clients append ?v=BUILD to cache-bust frames on each (re)deploy
DEFAULT_PORT = 8770
DISC_PORT = 8771
DISC_MAGIC = b"BITRATE_BRAWL_DISCOVER"
DISC_REPLY = b"BITRATE_BRAWL_HOST "

N = 26
MAX_N = 3000                           # ceiling for a per-player pool; Emma's voice mode can sweep N up to here to benchmark
BIT_PER_CHAR = math.log2(N - 1)        # 4.64 bits per correct letter
DURATION = 60.0
HP_MAX = round(20.0 * DURATION)         # 1200: only a ~20 bps run can deplete it in 60 s


# ---------------------------------------------------------------- networking utils
def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def all_ipv4():
    """Every plausible LAN IPv4 of this machine, primary (default-route) first. A PC with virtual
    adapters (VMware/WSL/Oculus) has several; the opponent must use the one on THEIR subnet, so we
    list them all instead of guessing one."""
    ips, primary = [], lan_ip()
    if primary and not primary.startswith("127."):
        ips.append(primary)
    try:
        for res in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = res[4][0]
            if ip and ip not in ips and not ip.startswith(("127.", "169.254.")):
                ips.append(ip)
    except OSError:
        pass
    return ips or ["127.0.0.1"]


def broadcast_targets():
    """Several broadcast forms so discovery survives macOS/Windows + phone-hotspot quirks: the
    limited broadcast plus the /24 directed broadcast of our own address (e.g. 192.168.1.255,
    172.20.10.255 on an iPhone hotspot)."""
    addrs = ["255.255.255.255"]
    ip = lan_ip()
    if ip.count(".") == 3 and not ip.startswith("127."):
        addrs.append(ip.rsplit(".", 1)[0] + ".255")
    return addrs


def discover_host(timeout=1.5):
    """Broadcast a probe; return 'ip:port' of an existing host, or None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.3)
    targets = broadcast_targets()
    deadline = time.monotonic() + timeout
    try:
        for _ in range(4):
            for bcast in targets:
                try:
                    s.sendto(DISC_MAGIC, (bcast, DISC_PORT))
                except OSError:
                    pass
            while time.monotonic() < deadline:
                try:
                    data, _addr = s.recvfrom(1024)
                except socket.timeout:
                    break
                except OSError:
                    return None
                if data.startswith(DISC_REPLY):
                    return data[len(DISC_REPLY):].decode("ascii", "ignore").strip()
            if time.monotonic() >= deadline:
                break
    finally:
        s.close()
    return None


def start_host_responder(port):
    """Reply to LAN discovery probes with our ip:port so the other machine can auto-join."""
    def run():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", DISC_PORT))
        except OSError:
            return                      # discovery unavailable; URL/QR fallback still works
        ip = lan_ip()
        reply = DISC_REPLY + ("%s:%d" % (ip, port)).encode("ascii")
        while True:
            try:
                data, addr = s.recvfrom(1024)
            except OSError:
                break
            if data.startswith(DISC_MAGIC):
                try:
                    s.sendto(reply, addr)
                except OSError:
                    pass
    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- the match (referee)
class Match:
    """One fight between up to two players. Server is authoritative for HP, score and the winner."""

    def __init__(self):
        self.lock = threading.RLock()
        self.clients = {}              # pid -> Queue (the player's CURRENT live SSE outbox)
        self.slots = {1: None, 2: None}  # pid -> owner token (survives brief reconnects)
        self.gen = {1: 0, 2: 0}        # bumped each (re)connection, to ignore stale disconnects
        self.ready = {1: False, 2: False}
        self.bnet = {1: 0.0, 2: 0.0}   # running net BITS (flat = bpc*(correct-wrong); Emma sends her surprisal bits)
        self.bpeak = {1: 0.0, 2: 0.0}  # best cumulative net bits so far -> drives damage (no healing)
        self.sc = {1: 0, 2: 0}
        self.si = {1: 0, 2: 0}
        self.state = "lobby"           # lobby -> countdown -> fight -> over
        self.start_time = None
        self.winner = None
        self.timer = None
        self.bot = None                # solo mode: {"pid": <bot seat>, "bps": <target>}, else None
        self.npc = {1: N, 2: N}        # alphabet size per player (a profile can shrink it); drives that player's bits

    # ---- membership (token-keyed so a brief EventSource reconnect reclaims the SAME slot) ----
    def join(self, token):
        with self.lock:
            pid = next((p for p in (1, 2) if self.slots[p] == token), None)   # reconnect
            if pid is None:
                pid = next((p for p in (1, 2) if self.slots[p] is None), None)  # new player
            if pid is None:
                return None, None, 0                                          # full -> spectator
            self.slots[pid] = token
            self.gen[pid] += 1
            q = queue.Queue()
            self.clients[pid] = q
            if self.state == "over":
                self._reset_to_lobby()     # a (re)join after a finished match -> fresh lobby so Ready works again
            else:
                self._broadcast_lobby()
            return pid, q, self.gen[pid]

    def leave(self, pid, gen, token):
        with self.lock:
            if pid is None or self.gen[pid] != gen:
                return                 # a newer connection already took over -> ignore stale close
            self.clients.pop(pid, None)
            self._broadcast_lobby()    # show "reconnecting…" immediately

        def free_later():
            with self.lock:
                if self.gen[pid] == gen and self.slots[pid] == token:          # really gone, no reconnect
                    self.slots[pid] = None
                    self.ready[pid] = False
                    other = 2 if pid == 1 else 1
                    if self.bot is not None and self.bot["pid"] == other:
                        self._reset_to_lobby()       # human left a solo match -> tear it down (clears the bot)
                    elif self.state in ("countdown", "fight") and not self.winner and self.slots[other]:
                        self._finish(winner=other, reason="opponent left")
                    else:
                        self._broadcast_lobby()
        threading.Timer(4.0, free_later).start()

    # ---- helpers ----
    def _put(self, pid, ev):
        q = self.clients.get(pid)
        if q is not None:
            q.put(ev)

    def _broadcast(self, ev):
        for pid in list(self.clients):
            self._put(pid, ev)

    def bpc(self, pid):
        return math.log2(max(2, self.npc[pid]) - 1)    # bits per correct selection for this player's alphabet

    def hp(self):
        return {1: max(0, round(HP_MAX - self.bpeak[2])),   # p1 HP hurt by p2's damage (bit-score)
                2: max(0, round(HP_MAX - self.bpeak[1]))}

    def _present(self, pid):
        # a seat counts as present if a real client holds it, or the computer occupies it (solo)
        return pid in self.clients or (self.bot is not None and self.bot["pid"] == pid)

    def _broadcast_lobby(self):
        self._broadcast({"t": "lobby", "present": [p for p in (1, 2) if self._present(p)],
                         "ready": self.ready, "hpMax": HP_MAX, "n": N, "state": self.state})

    # ---- actions ----
    def set_profile(self, pid, n):
        # the client reports its alphabet size (Calvin/Elizabeth = 26, Emma's spoken set is smaller)
        with self.lock:
            if pid in (1, 2):
                self.npc[pid] = max(2, min(MAX_N, int(n)))

    def set_ready(self, pid, val):
        with self.lock:
            if self.state != "lobby":
                return
            self.ready[pid] = bool(val)
            self._broadcast_lobby()
            if self._present(1) and self._present(2) and self.ready[1] and self.ready[2]:
                self._begin_countdown()

    def _begin_countdown(self):
        self.state = "countdown"
        self._broadcast({"t": "countdown", "secs": 3, "solo": self.bot is not None})
        threading.Timer(4.0, self._begin_fight).start()   # 3-2-1 (3s) + FIGHT! (1s); round starts when FIGHT! clears

    def _begin_fight(self):
        with self.lock:
            if self.state != "countdown":
                return
            self.state = "fight"
            self.start_time = time.monotonic()
            self._broadcast({"t": "fight", "duration": DURATION, "hp": self.hp()})
            self.timer = threading.Timer(DURATION, self._on_timeout)
            self.timer.start()
            if self.bot is not None:
                threading.Thread(target=self._bot_loop, args=(self.bot,), daemon=True).start()

    def _bot_loop(self, bot):
        # The computer opponent. It completes 4-letter blocks at randomized intervals whose average
        # yields ~bps bits/second of damage (each interval scales with that block's bits, so the
        # realized rate self-corrects to the target). Mostly clean, with an occasional slip. The block
        # is chosen AND applied while holding the lock and checking `self.bot is bot` (the exact dict
        # this thread was started for), so a finished/reset/replaced game can never take a stale hit.
        pid, bps = bot["pid"], bot["bps"]
        time.sleep(random.uniform(0.5, 1.1))              # don't strike the instant the round opens
        kind = 0
        while True:
            with self.lock:
                if self.state != "fight" or self.bot is not bot:
                    return
                correct, wrong = (3, 1) if random.random() < 0.15 else (4, 0)
                self.attack(pid, correct, wrong, kind)
            kind = (kind + 1) % 5
            bits = BIT_PER_CHAR * max(0, correct - wrong)
            end = time.monotonic() + (bits / bps) * random.uniform(0.7, 1.3)
            while time.monotonic() < end:
                if self.state != "fight" or self.bot is not bot:
                    return
                time.sleep(0.05)

    def attack(self, pid, correct, wrong, kind, n=N, bits=None):
        with self.lock:
            if self.state != "fight":
                return
            self.npc[pid] = max(2, min(MAX_N, int(n)))
            correct = max(0, int(correct)); wrong = max(0, int(wrong))
            self.sc[pid] += correct
            self.si[pid] += wrong
            # block damage in bits: a client-supplied surprisal sum (Emma) or the flat bpc * net
            block = float(bits) if bits is not None else self.bpc(pid) * (correct - wrong)
            self.bnet[pid] += block
            if self.bnet[pid] > self.bpeak[pid]:
                self.bpeak[pid] = self.bnet[pid]
            dmg = round(max(0.0, block))
            hp = self.hp()
            other = 2 if pid == 1 else 1
            self._broadcast({"t": "hit", "by": pid, "on": other, "dmg": dmg,
                             "kind": int(kind) % 5, "hp": hp,
                             "combo": None})
            if hp[other] <= 0:
                self._finish(winner=pid, reason="K.O.")

    def _on_timeout(self):
        with self.lock:
            if self.state != "fight":
                return
            hp = self.hp()
            if hp[1] > hp[2]:
                w = 1
            elif hp[2] > hp[1]:
                w = 2
            else:
                w = 0                  # draw
            self._finish(winner=w, reason="time")

    def _finish(self, winner, reason):
        if self.state == "over":
            return
        self.state = "over"
        self.winner = winner
        if self.timer:
            self.timer.cancel()
        el = (time.monotonic() - self.start_time) if self.start_time else DURATION
        el = max(1e-6, min(el, DURATION))
        stats = {}
        for pid in (1, 2):
            b = max(0.0, self.bnet[pid]) / el
            stats[pid] = {"sc": self.sc[pid], "si": self.si[pid], "B": round(b, 2),
                          "dmg": round(self.bpeak[pid]), "n": self.npc[pid]}
        self._broadcast({"t": "over", "winner": winner, "reason": reason,
                         "hp": self.hp(), "stats": stats, "n": N, "elapsed": round(el, 1)})

    def _reset_to_lobby(self):
        # reset the round but keep connected players; caller must hold self.lock
        self._clear_bot()
        self.ready = {1: False, 2: False}
        self.bnet = {1: 0.0, 2: 0.0}; self.bpeak = {1: 0.0, 2: 0.0}
        self.sc = {1: 0, 2: 0}; self.si = {1: 0, 2: 0}; self.npc = {1: N, 2: N}   # clear per-player alphabets between rounds
        self.state = "lobby"; self.start_time = None; self.winner = None
        if self.timer:
            self.timer.cancel(); self.timer = None
        self._broadcast({"t": "reset"})
        self._broadcast_lobby()

    def rematch(self, pid):
        with self.lock:
            if self.state != "over":
                return
            self._reset_to_lobby()

    def kick(self, by_pid):
        # Either live player can remove the other one (e.g. a squatter who never readies up),
        # freeing that seat so someone else can take it. The kicker keeps their own seat.
        with self.lock:
            if by_pid not in (1, 2) or by_pid not in self.clients:
                return                              # only a connected player may kick
            other = 2 if by_pid == 1 else 1
            if self.slots[other] is None and other not in self.clients:
                return                              # nobody in the other seat
            self._put(other, {"t": "kicked"})       # tell them, while their outbox still exists
            self.clients.pop(other, None)
            self.slots[other] = None
            self.ready[other] = False
            self.gen[other] += 1                    # stale-out the kicked connection's slot claim
            self._reset_to_lobby()                  # fresh lobby for whoever remains

    def start_solo(self, human_pid, bps):
        # Optional single-player mode: fill the empty seat with a computer that "types" at ~bps
        # bits/second, so the human has to out-transmit it to win. The 2-player game is unchanged.
        with self.lock:
            if human_pid not in (1, 2) or human_pid not in self.clients:
                return
            if self.state == "over":
                self._reset_to_lobby()              # allow replay-solo straight from the end screen
            if self.state != "lobby":
                return
            other = 2 if human_pid == 1 else 1
            if self.slots[other] is not None or other in self.clients:
                return                              # a real player holds the other seat -> no solo
            self.slots[other] = "BOT"
            self.ready[other] = True
            self.bot = {"pid": other, "bps": max(1.0, min(30.0, float(bps)))}
            self.ready[human_pid] = True
            self._broadcast_lobby()
            if self.ready[1] and self.ready[2]:
                self._begin_countdown()

    def _clear_bot(self):
        if self.bot is not None:
            bp = self.bot["pid"]
            if self.slots.get(bp) == "BOT":
                self.slots[bp] = None
            self.ready[bp] = False
            self.bot = None


# ---------------------------------------------------------------- HTTP handler
class Handler(BaseHTTPRequestHandler):
    server_version = "StreetTyper/1.0"

    def log_message(self, *a):
        pass

    def _nocache(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._nocache()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        # lightweight existence check (the client uses it to detect the optional offline voice model)
        rel = urlparse(self.path).path.lstrip("/").replace("/", os.sep)
        full = os.path.normpath(os.path.join(HERE, rel))
        ok = (full == HERE or full.startswith(HERE + os.sep)) and os.path.isfile(full)
        self.send_response(200 if ok else 404)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._serve_html()
        if path == "/lan":
            port = self.server.server_address[1]
            return self._json({"urls": ["http://%s:%d/" % (ip, port) for ip in all_ipv4()],
                               "port": port})
        if path == "/sync":
            return self._serve_sync()
        if path.startswith("/characters/") or path.startswith("/assets/"):
            return self._serve_static(path)
        self.send_error(404)

    def _serve_static(self, path):
        rel = path.lstrip("/").replace("/", os.sep)
        full = os.path.normpath(os.path.join(HERE, rel))
        if not (full == HERE or full.startswith(HERE + os.sep)) or not os.path.isfile(full):
            return self.send_error(404)
        ext = os.path.splitext(full)[1].lower()
        ctype = {".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json",
                 ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".gif": "image/gif", ".mp3": "audio/mpeg", ".ogg": "audio/ogg",
                 ".wav": "audio/wav", ".m4a": "audio/mp4"}.get(ext, "application/octet-stream")
        try:
            with open(full, "rb") as f:
                body = f.read()
        except OSError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if ext in (".png", ".gz", ".tar", ".wasm"):
            # cache frames (img-swaps stay instant) and the large offline voice model (.tar.gz),
            # so they are not refetched every visit; the client cache-busts frames with ?v=BUILD.
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self._nocache()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/event":
            return self.send_error(404)
        try:
            n = int(self.headers.get("Content-Length", 0))
            ev = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"ok": False}, 400)
        m = self.server.match
        pid = int(ev.get("pid", 0))
        t = ev.get("t")
        if pid in (1, 2):
            if t == "ready":
                m.set_ready(pid, ev.get("ready", True))
            elif t == "attack":
                m.attack(pid, ev.get("correct", 0), ev.get("wrong", 0), ev.get("kind", 0), ev.get("n", N), ev.get("bits"))
            elif t == "rematch":
                m.rematch(pid)
            elif t == "kick":
                m.kick(pid)
            elif t == "solo":
                m.start_solo(pid, ev.get("bps", 10))
            elif t == "profile":
                m.set_profile(pid, ev.get("n", N))
        return self._json({"ok": True})

    def _serve_html(self):
        try:
            with open(os.path.join(HERE, "fight.html"), "rb") as f:
                body = f.read()
        except OSError:
            return self.send_error(500, "fight.html not found")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._nocache()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_sync(self):
        m = self.server.match
        qs = parse_qs(urlparse(self.path).query)
        token = (qs.get("token", [""])[0] or "anon")[:64]
        pid, q, gen = m.join(token)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self._nocache()
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            port = self.server.server_address[1]
            urls = ["http://%s:%d/" % (ip, port) for ip in all_ipv4()]
            self._sse({"t": "welcome", "you": pid, "hpMax": HP_MAX, "n": N, "build": BUILD,
                       "lanUrl": urls[0], "lanUrls": urls})
            if pid is None:
                self._sse({"t": "full"})
                return
            m._broadcast_lobby()
            while True:
                try:
                    ev = q.get(timeout=0.5)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self._sse(ev)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            m.leave(pid, gen, token)

    def _sse(self, obj):
        self.wfile.write(("data: " + json.dumps(obj) + "\n\n").encode())
        self.wfile.flush()


def main():
    ap = argparse.ArgumentParser(description="Street Typer - live typing fight (stdlib only).")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    ap.add_argument("--host-only", action="store_true", help="force hosting (skip auto-join discovery)")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--cloud", action="store_true",
                    help="hosted mode: just serve on $PORT, no browser, no LAN discovery")
    args = ap.parse_args()
    cloud = args.cloud or bool(os.environ.get("PORT"))     # hosting platforms (Render/Railway/...) set $PORT

    # LAN auto-join is only meaningful on a local network; never in the cloud
    if not cloud and not args.host_only:
        found = discover_host()
        if found:
            url = "http://%s/" % found
            print(">> Found a host on the LAN -> joining the fight at %s" % url)
            if not args.no_browser:
                webbrowser.open(url)
            print("   (Player 2) The game is in your browser; this window can stay open.")
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                return

    httpd = ThreadingHTTPServer(("", args.port), Handler)
    httpd.match = Match()
    if cloud:
        print("=" * 64)
        print(" STREET TYPER  -  hosted mode, listening on port %d" % args.port)
        print(" Both players open the public URL. First to load = Player 1, second = Player 2.")
        print("=" * 64)
    else:
        start_host_responder(args.port)
        print("=" * 64)
        print(" STREET TYPER  -  you are the HOST (Player 1). Browser opens automatically.")
        print(" Player 2 (other computer): run python fight_server.py -> it auto-joins. If that fails,")
        print(" open ONE of these on the other computer (try in order until one loads):")
        for ip in all_ipv4():
            print("        http://%s:%d/" % (ip, args.port))
        print("=" * 64)
        if not args.no_browser:
            threading.Timer(0.6, lambda: webbrowser.open("http://127.0.0.1:%d/" % args.port)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n>> bye")


if __name__ == "__main__":
    main()
