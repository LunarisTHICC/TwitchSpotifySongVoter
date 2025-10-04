# TwitchSpotifySongVoter
A simple way to let your Twitch chat vote on the next Spotify track, show a clean dark-themed web page with the current song and queue, and give the streamer a host controller window to manage the queue (including a subtle “−” button to remove queued songs).

Overview
• 	What this does:
• 	Viewers type  to open a voting page and request songs.
• 	The system finds the best match on Spotify and builds a queue.
• 	The web page shows the current track cover, title, artist, and “In Queue.”
• 	A small DMCA label appears under the song title (minimal and unobtrusive).
• 	The streamer gets a host controller window that mirrors the web page and adds a “−” button on each queued song to remove it manually.
• 	What you run:
• 	A server (FastAPI) that exposes the web UI, a WebSocket for live updates, and APIs.
• 	A Twitch bot (twitchio) that listens to chat commands.
• 	A host controller GUI (Tkinter) for the streamer.

What you need
• 	Computer: Windows 10 or 11 (you can run on other platforms, but this guide is Windows‑first).
• 	Basic tools:
• 	Python 3.10+ installed and added to PATH.
• 	Accounts and keys:
• 	Spotify:
• 	Client ID and Client Secret from the Spotify Developer Dashboard.
• 	Refresh Token (obtained via OAuth once; it lets the app keep controlling playback).
• 	Device ID (the target Spotify Connect device—usually the desktop app on your PC).
• 	Twitch:
• 	OAuth Token for your bot (the “password” the bot uses to log in).
• 	Channel name (the channel the bot joins).
Tip: If you’ve never used developer dashboards, don’t worry. Just look for “Create App,” name it, and you’ll see fields like Client ID and Client Secret. For the refresh token and device ID, follow any standard Spotify OAuth guide—save these values in your  file.

	Setup in 10 minutes
	1. 	Install Python packages
• 	Open Command Prompt and run:

pip install -r requirements.txt

	1. 	If you don’t have , create it with:
	
fastapi
uvicorn
aiohttp
twitchio
Pillow
python-dotenv

	2. 	Create your environment file
• 	Copy  to  and fill in the values:

SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REFRESH_TOKEN=your_spotify_refresh_token
SPOTIFY_DEVICE_ID=your_spotify_device_id

TWITCH_OAUTH_TOKEN=oauth:your_twitch_oauth_token
TWITCH_CHANNEL=yourchannelname

• 	Save the file in the same folder as , , and .
	3. 	Place files together
• 	Keep these files in one folder:
• 	server.py (FastAPI server with WebSocket)
• 	bot.py (Twitch bot)
• 	host_gui.py (Streamer’s controller UI)
• 	static/index.html (web voting page)
• 	requirements.txt and .env
• 	run.bat (Windows launcher)

	Launch
• 	Easiest method (Windows):
• 	Double‑click .
• 	Three windows open: Server, Twitch Bot, and Host GUI.
• 	What you’ll see:
• 	Web page at:

http://localhost:3000/static/index.html

• 	Bot joins your Twitch channel (using your OAuth token).
• 	Host controller GUI window shows current song and queue with “−” buttons.
• 	If you prefer a single Python command:

python main.py


• 	Run:

• 	This spawns server, bot, and host GUI in one shot (if you’re using the provided ).

	Using it
• 	In Twitch chat:
• 	Command: !interactive
• 	Bot replies with the voting link (the web page).
• 	Command: !vote your song name
• 	Adds a vote/request; the system resolves to a Spotify track/album/playlist.
• 	On the web page (for viewers):
• 	Current song: Large cover, title, artist, duration, small DMCA label.
• 	In Queue: List of upcoming items with thumbnails.
• 	Vote box: Type a song/artist/album/playlist and submit.
• 	In the host controller (for streamer):
• 	Sees the same info as the web page.
• 	Uses the subtle “−” button on any queued item to remove it immediately.
• 	Toggles voting Enabled/Disabled without breaking the bot or server connections.
• 	Playback flow:
• 	The current song plays on the streamer’s Spotify.
• 	When it ends, the next queued item auto‑plays.
• 	The UI and GUI update live via WebSockets.

	Troubleshooting and tips
• 	If the web page doesn’t load:
• 	Confirm the server window shows “Server running on http://localhost:3000”.
• 	Some systems auto‑select a nearby port (3001, 3002, …). Check the server window for the actual port and update the link accordingly.
• 	If the bot doesn’t join your channel:
• 	Verify your TWITCH_OAUTH_TOKEN and TWITCH_CHANNEL in .env.
• 	Make sure your channel name is lowercase and correct.
• 	If Spotify won’t play:
• 	Ensure your Spotify desktop app is open and logged in.
• 	Verify SPOTIFY_DEVICE_ID matches the active device.
• 	Double‑check Client ID, Client Secret, and Refresh Token are correct.
• 	DMCA label:
• 	The DMCA indicator is minimal by design. You can wire it to your own whitelist/blacklist logic later. For now, it’s an informational indicator only.
• 	Avoiding conflicts with other apps:
• 	The WebSocket uses a namespaced path (/ws/v1) and a custom subprotocol to avoid collisions.
• 	The server picks a free port automatically and prevents duplicate launches with a small lock file.
• 	Stopping everything:
• 	Close each window (Server, Bot, GUI).
• 	Or end them from Task Manager if needed.
If you want a Mac/Linux launcher, add a simple un.py that starts all three Python processes—same idea as the Windows batch file.
