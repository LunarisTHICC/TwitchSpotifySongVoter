# host_gui.py
import os
import asyncio
import threading
import json
import tkinter as tk
from tkinter import ttk
from io import BytesIO
from PIL import Image, ImageTk
import aiohttp

API_BASE = os.getenv("API_BASE", "http://localhost:3000")
WS_URL = API_BASE.replace("http", "ws") + "/ws/v1"

class HostGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Music Controller")
        self.root.configure(bg="#121212")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#121212", foreground="#ffffff")
        style.configure("TButton", background="#9146FF", foreground="#ffffff")
        style.map("TButton", background=[("active","#7a3cf0")])

        self.enabled_var = tk.StringVar(value="Enabled")
        top = ttk.Frame(root)
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Interactive Voting UI", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(top, textvariable=self.enabled_var, command=self.toggle).pack(side="right")

        self.current_cover = ttk.Label(root)
        self.current_cover.pack(padx=10, pady=(0,6))
        self.current_meta = ttk.Label(root, text="—", font=("Segoe UI", 10))
        self.current_meta.pack(padx=10, pady=(0,10))

        ttk.Label(root, text="In queue", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)
        self.queue_frame = ttk.Frame(root)
        self.queue_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(root, text="Live requests", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10)
        self.req_frame = ttk.Frame(root)
        self.req_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.images_cache = {}

        # Start asyncio receiver in thread
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        asyncio.run_coroutine_threadsafe(self.ws_receiver(), self.loop)

    async def toggle(self):
        async with aiohttp.ClientSession() as session:
            # Flip current state
            async with session.get(f"{API_BASE}/api/state") as resp:
                s = await resp.json()
                next_enabled = not s.get("enabled", True)
            async with session.post(f"{API_BASE}/api/toggle", json={"enabled": next_enabled}) as resp:
                self.enabled_var.set("Enabled" if next_enabled else "Disabled")

    def render_current(self, cur):
        meta = f"{cur.get('title','—')} — {cur.get('artist','—')}\nDMCA: {cur.get('dmca','approved').capitalize()}"
        self.current_meta.config(text=meta)
        cover_url = cur.get("cover","")
        if cover_url:
            asyncio.run_coroutine_threadsafe(self.load_image(cover_url, self.current_cover, size=(128,128)), self.loop)

    def render_queue(self, items):
        for w in self.queue_frame.winfo_children():
            w.destroy()
        for it in items:
            row = ttk.Frame(self.queue_frame)
            row.pack(fill="x", pady=4)
            img_lbl = ttk.Label(row)
            img_lbl.pack(side="left")
            # load cover async
            cover_url = it.get("cover","")
            if cover_url:
                asyncio.run_coroutine_threadsafe(self.load_image(cover_url, img_lbl, size=(48,48)), self.loop)

            text = ttk.Label(row, text=f"{it.get('title','—')} — {it.get('artist','')}")
            text.pack(side="left", padx=8)
            # Host-only removal control (the “−” button)
            btn = ttk.Button(row, text="−", width=2, command=lambda u=it.get("uri"): self.remove_from_queue(u))
            btn.pack(side="right")

    def render_requests(self, items):
        for w in self.req_frame.winfo_children():
            w.destroy()
        for it in items:
            row = ttk.Frame(self.req_frame)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=f"{it.get('title', it.get('query','—'))} ({it.get('votes',1)} vote{'s' if it.get('votes',1)>1 else ''})").pack(side="left")

    async def remove_from_queue(self, uri):
        async with aiohttp.ClientSession() as session:
            await session.post(f"{API_BASE}/api/remove", json={"uri": uri})

    async def load_image(self, url, widget, size=(64,64)):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            img = Image.open(BytesIO(data)).resize(size, Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            widget.image = tkimg  # keep ref
            widget.configure(image=tkimg)
        except Exception:
            pass

    async def ws_receiver(self):
        # Use namespaced WS with subprotocol to avoid interference
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(WS_URL, protocols=("interactive-v1",)) as ws:
                await ws.send_str("ping")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            payload = json.loads(msg.data)
                        except Exception:
                            continue
                        if payload.get("type") == "state":
                            cur = payload.get("current")
                            if cur: self.render_current(cur)
                            self.render_queue(payload.get("queue", []))
                            self.enabled_var.set("Enabled" if payload.get("enabled", True) else "Disabled")
                        elif payload.get("type") == "results":
                            self.render_requests(payload.get("items", []))
                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                        break

def main():
    root = tk.Tk()
    gui = HostGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()