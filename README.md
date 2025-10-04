# Readme

A simple way to let your Twitch chat vote on the next Spotify track, show a clean dark-themed web page with the current song and queue, and give the streamer a host controller window to manage the queue (including a subtle “−” button to remove queued songs).

---

## Overview

**What this does:**
- Viewers type `!interactive` to open a voting page and request songs.
- The system finds the best match on Spotify and builds a queue.
- The web page shows the current track cover, title, artist, and “In Queue.”
- A small DMCA label appears under the song title (minimal and unobtrusive).
- The streamer gets a host controller window that mirrors the web page and adds a “−” button on each queued song to remove it manually.

**What you run:**
- A server (FastAPI) that exposes the web UI, a WebSocket for live updates, and APIs.
- A Twitch bot (twitchio) that listens to chat commands.
- A host controller GUI (Tkinter) for the streamer.

---

## What you need

- **Computer:** Windows 10 or 11 (you can run on other platforms, but this guide is Windows‑first).
- **Basic tools:**
  - Python 3.10+ installed and added to PATH.
- **Accounts and keys:**
  - **Spotify:**
    - Client ID and Client Secret from the Spotify Developer Dashboard.
    - Refresh Token (obtained via OAuth once; it lets the app keep controlling playback).
    - Device ID (the target Spotify Connect device—usually the desktop app on your PC).
  - **Twitch:**
    - OAuth Token for your bot (the “password” the bot uses to log in).
    - Channel name (the channel the bot joins).

> **Tip:** If you’ve never used developer dashboards, don’t worry. Just look for “Create App,” name it, and you’ll see fields like Client ID and Client Secret. For the refresh token and device ID, follow any standard Spotify OAuth guide—save these values in your `.env` file.

---

## Setup in 10 minutes

1. **Install Python packages**
   - Open Command Prompt and run:
     ```bash
     pip install -r requirements.txt
     ```

   - If you don’t have `requirements.txt`, create it with:
     ```txt
     fastapi
     uvicorn
     aiohttp
     twitchio
     Pillow
     python-dotenv
     ```

2. **Create your environment file**
   - Copy `.env.example` to `.env` and fill in the values:
     ```ini
     SPOTIFY_CLIENT_ID=your_spotify_client_id
     SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
     SPOTIFY_REFRESH_TOKEN=your_spotify_refresh_token
     SPOTIFY_DEVICE_ID=your_spotify_device_id

     TWITCH_OAUTH_TOKEN=oauth:your_twitch_oauth_token
     TWITCH_CHANNEL=yourchannelname
     ```
   - Save the file in the same folder as `server.py`, `bot.py`, and `host_gui.py`.

3. **Place files together**
   - Keep these files in one folder:
     - `server.py` (FastAPI server with WebSocket)
     - `bot.py` (Twitch bot)
     - `host_gui.py` (Streamer’s controller UI)
     - `static/index.html` (web voting page)
     - `requirements.txt` and `.env`
     - `run.bat` (Windows launcher)

---

## Launch

- **Easiest method (Windows):**
  - Double‑click `run.bat`.
  - Three windows open: Server, Twitch Bot, and Host GUI.

- **What you’ll see:**
  - Web page at:
    ```
    http://localhost:3000/static/index.html
    ```
  - Bot joins your Twitch channel (using your OAuth token).
  - Host controller GUI window shows current song and queue with “−” buttons.

- **If you prefer a single Python command:**
  ```bash
  python main.py
