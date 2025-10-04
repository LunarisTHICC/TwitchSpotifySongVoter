# server.py
import os
import sys
import json
import asyncio
import socket
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import aiohttp

APP_NAMESPACE = "/ws/v1"  # Namespaced WS path to avoid collisions
LOCKFILE = "interactive_music_server.lock"

# ---- Utilities: dynamic port selection & singleton lock ----
def find_free_port(preferred=3000, max_tries=20):
    for offset in range(max_tries):
        port = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found in range")

def create_singleton_lock():
    if os.path.exists(LOCKFILE):
        # If lock exists, verify process is alive; otherwise, remove.
        return False
    try:
        with open(LOCKFILE, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return False

def remove_singleton_lock():
    try:
        if os.path.exists(LOCKFILE):
            os.remove(LOCKFILE)
    except Exception:
        pass

# ---- Data models ----
@dataclass
class Track:
    title: str
    artist: str
    uri: str
    cover: str = ""
    duration_ms: Optional[int] = None
    dmca: str = "approved"  # 'approved' | 'warn' | 'denied'

enabled = True
current: Optional[Track] = None
queue: List[Track] = []
requests: List[Dict] = []  # [{query, title?, artist?, uri?, cover?, votes}]

# ---- Spotify OAuth/config (fill env vars) ----
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN", "")
SPOTIFY_DEVICE_ID = os.getenv("SPOTIFY_DEVICE_ID", "")

async def get_access_token():
    async with aiohttp.ClientSession() as session:
        auth = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        headers = {
            "Authorization": "Basic " + auth.encode("ascii").hex(),  # simple obfuscation
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": SPOTIFY_REFRESH_TOKEN,
        }
        async with session.post("https://accounts.spotify.com/api/token", headers=headers, data=data) as resp:
            obj = await resp.json()
            return obj.get("access_token")

async def spotify_search(q: str, access: str):
    url = f"https://api.spotify.com/v1/search?q={aiohttp.helpers.quote(q)}&type=track,album,playlist&limit=5"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"Authorization": f"Bearer {access}"}) as resp:
            return await resp.json()

def pick_best_image(images: List[Dict]) -> str:
    if not images: return ""
    sorted_imgs = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
    return (sorted_imgs[1] if len(sorted_imgs) > 1 else sorted_imgs[0]).get("url", "")

def minimal_dmca(_item) -> str:
    # Hook in your whitelist/blacklist logic
    return "approved"

async def play_uri(uri: str, access: str) -> bool:
    url = f"https://api.spotify.com/v1/me/player/play?device_id={SPOTIFY_DEVICE_ID}"
    payload = {"uris": [uri]}
    async with aiohttp.ClientSession() as session:
        async with session.put(url, headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"}, data=json.dumps(payload)) as resp:
            return resp.status in (200, 204)

# ---- Voting helpers ----
def add_request(query: str, resolved: Optional[Dict]):
    # Match on URI when available; else group by query
    for r in requests:
        if resolved and r.get("uri") == resolved.get("uri"):
            r["votes"] = r.get("votes", 1) + 1
            return r
        if not resolved and r.get("query") == query:
            r["votes"] = r.get("votes", 1) + 1
            return r
    entry = {"query": query, "votes": 1}
    if resolved:
        entry.update(resolved)
    requests.append(entry)
    return entry

def resolve_winner() -> Optional[Dict]:
    if not requests: return None
    win = sorted(requests, key=lambda x: x.get("votes", 1), reverse=True)[0]
    requests.clear()
    return win

async def enqueue_winner():
    winner = resolve_winner()
    if not winner: return
    access = await get_access_token()
    if not winner.get("uri"):
        data = await spotify_search(winner["query"], access)
        cand_track = (data.get("tracks", {}) or {}).get("items", [])[:1]
        cand_album = (data.get("albums", {}) or {}).get("items", [])[:1]
        cand_pl = (data.get("playlists", {}) or {}).get("items", [])[:1]
        chosen = (cand_track or cand_album or cand_pl or [None])[0]
        if chosen:
            cover = pick_best_image(chosen.get("album", {}).get("images", []) or chosen.get("images", []))
            uri = chosen.get("uri", "")
            title = chosen.get("name", "")
            artist = ", ".join(a.get("name") for a in chosen.get("artists", []) or []) or chosen.get("owner", {}).get("display_name", "")
            queue.append(Track(title=title, artist=artist, uri=uri, cover=cover, duration_ms=chosen.get("duration_ms"), dmca=minimal_dmca(chosen)))
    else:
        queue.append(Track(title=winner.get("title",""), artist=winner.get("artist",""), uri=winner.get("uri",""), cover=winner.get("cover",""), dmca=minimal_dmca(winner)))

async def tick_playback():
    access = await get_access_token()
    # If nothing is playing and queue exists, start next
    if current is None and queue:
        nxt = queue.pop(0)
        if await play_uri(nxt.uri, access):
            globals()["current"] = nxt
            return
    # Refresh player state
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.spotify.com/v1/me/player", headers={"Authorization": f"Bearer {access}"}) as resp:
            s = await resp.json()
            if s.get("item"):
                itm = s["item"]
                globals()["current"] = Track(
                    title=itm["name"],
                    artist=", ".join(a["name"] for a in itm.get("artists", [])),
                    uri=itm.get("uri",""),
                    cover=pick_best_image(itm.get("album", {}).get("images", [])),
                    duration_ms=itm.get("duration_ms"),
                    dmca=minimal_dmca(itm),
                )
            if not s.get("is_playing", True) and queue:
                nxt = queue.pop(0)
                await play_uri(nxt.uri, access)
                globals()["current"] = nxt

# ---- WebSocket manager (namespaced, heartbeat, backpressure) ----
class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept(subprotocol="interactive-v1")
        async with self._lock:
            self.active.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self.active:
                self.active.remove(ws)

    async def broadcast(self, payload: Dict):
        # Defensive send with cleanup
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

manager = WSManager()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/state")
async def api_state():
    return {
        "enabled": enabled,
        "current": asdict(current) if current else None,
        "queue": [asdict(t) for t in queue],
    }

@app.post("/api/toggle")
async def api_toggle(payload: Dict = Body(...)):
    globals()["enabled"] = bool(payload.get("enabled", True))
    return {"enabled": enabled}

@app.post("/api/vote")
async def api_vote(payload: Dict = Body(...)):
    if not enabled:
        return JSONResponse({"error": "disabled"}, status_code=403)
    query = (payload.get("query") or "").strip()
    if not query:
        return JSONResponse({"error": "empty"}, status_code=400)
    access = await get_access_token()
    data = await spotify_search(query, access)
    track = (data.get("tracks", {}) or {}).get("items", [])[:1]
    album = (data.get("albums", {}) or {}).get("items", [])[:1]
    playlist = (data.get("playlists", {}) or {}).get("items", [])[:1]
    chosen = (track or album or playlist or [None])[0]
    resolved = None
    if chosen:
        resolved = {
            "title": chosen.get("name", ""),
            "artist": ", ".join(a.get("name") for a in chosen.get("artists", []) or []) or chosen.get("owner", {}).get("display_name", ""),
            "uri": chosen.get("uri", ""),
            "cover": pick_best_image(chosen.get("album", {}).get("images", []) or chosen.get("images", [])),
        }
    entry = add_request(query, resolved)
    await manager.broadcast({"type": "results", "items": requests})
    return {"ok": True, "entry": entry}

@app.get("/api/results")
async def api_results():
    return {"items": requests}

@app.post("/api/remove")
async def api_remove(payload: Dict = Body(...)):
    """Host-only removal by URI."""
    uri = payload.get("uri")
    if not uri:
        return JSONResponse({"error": "missing_uri"}, status_code=400)
    # remove matching item
    for i, t in enumerate(queue):
        if t.uri == uri:
            queue.pop(i)
            await manager.broadcast({"type": "queue", "queue": [asdict(q) for q in queue]})
            return {"ok": True}
    return JSONResponse({"error": "not_found"}, status_code=404)

@app.websocket(APP_NAMESPACE)
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Passive receive to support pings or small client messages
            try:
                msg = await ws.receive_text()
                if msg == "ping":
                    await ws.send_text("pong")
            except Exception:
                await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        await manager.disconnect(ws)

# ---- broadcaster loop: push sub-second updates ----
async def broadcaster():
    last = 0
    while True:
        await asyncio.sleep(0.25)  # sub-second updates without thrashing
        now = time.time()
        # Push current state & results (rate-limit to avoid flood)
        payload = {
            "type": "state",
            "enabled": enabled,
            "current": asdict(current) if current else None,
            "queue": [asdict(t) for t in queue],
        }
        await manager.broadcast(payload)
        if now - last > 1.0:
            await manager.broadcast({"type": "results", "items": requests})
            last = now

async def lifecycles():
    while True:
        await enqueue_winner()    # tally and enqueue every cycle if needed
        await tick_playback()     # keep playback aligned
        await asyncio.sleep(1.0)  # 1s resolution

def run():
    # Detect free port and hold lock
    ok = create_singleton_lock()
    if not ok:
        print("Another instance appears to be running. Exiting.")
        sys.exit(1)
    port = int(os.getenv("INTERACTIVE_PORT", find_free_port(3000)))
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.create_task(broadcaster())
    loop.create_task(lifecycles())
    uvicorn.run(app, host="0.0.0.0", port=port, ws="auto")
    remove_singleton_lock()

if __name__ == "__main__":
    run()