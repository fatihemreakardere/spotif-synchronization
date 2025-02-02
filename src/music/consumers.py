import asyncio
import httpx
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SpotifyPlayerConsumer(AsyncWebsocketConsumer):
    channel_layer_alias = "default"  # added: override default channel layer reference

    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token_pair = [s for s in query_string.split("&") if s.startswith("token=")]
        if token_pair:
            self.access_token = token_pair[0].split("=")[1]
        else:
            self.access_token = None

        if not self.access_token:
            await self.close()
        else:
            await self.accept()
            self.loop_task = asyncio.create_task(self.player_loop())

    async def disconnect(self, close_code):
        if hasattr(self, "loop_task"):
            self.loop_task.cancel()

    async def player_loop(self):
        while True:
            status = await self.get_player_status()
            if status:
                await self.send(json.dumps(status))
            await asyncio.sleep(0)

    async def get_player_status(self):
        headers = {"Authorization": "Bearer " + self.access_token}
        player_url = "https://api.spotify.com/v1/me/player"
        async with httpx.AsyncClient() as client:
            response = await client.get(player_url, headers=headers)
            if response.status_code != 200:
                return None
            data = response.json()
            # Extract artist names from list of artist objects:
            artists = data.get("item", {}).get("artists", [])
            artist_names = ", ".join(artist.get("name") for artist in artists) if artists else "Unknown Artist"
            # Get album image from album object:
            album_art = ""
            album_info = data.get("item", {}).get("album", {})
            images = album_info.get("images", [])
            if images:
                album_art = images[0].get("url", "")
            return {
                "current_time": data.get("progress_ms"),
                "duration": data.get("item", {}).get("duration_ms"),
                "is_playing": data.get("is_playing"),
                "currently_playing": data.get("item", {}).get("name"),
                "artist": artist_names,
                "album_art": album_art,
                "curent_time_min_sec": f"{data.get('progress_ms') // 60000}:{str(data.get('progress_ms') % 60000 // 1000).zfill(2)}",
            }

    async def receive(self, text_data=None):
        # Handle control commands from client
        data = json.loads(text_data)
        command = data.get("command")
        if command:
            await self.control_playback(command)
        # Optionally, pass through other messages if needed
        # ...existing code...

    async def control_playback(self, command):
        # Map commands to their respective Spotify API endpoints and HTTP method
        url_map = {
            "play": {"url": "https://api.spotify.com/v1/me/player/play", "method": "PUT"},
            "pause": {"url": "https://api.spotify.com/v1/me/player/pause", "method": "PUT"},
            "next": {"url": "https://api.spotify.com/v1/me/player/next", "method": "POST"},
            "previous": {"url": "https://api.spotify.com/v1/me/player/previous", "method": "POST"},
        }
        entry = url_map.get(command)
        if not entry:
            await self.send(json.dumps({"status": "error", "message": "Unknown command"}))
            return

        headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            if entry["method"] == "PUT":
                response = await client.put(entry["url"], headers=headers)
            else:
                response = await client.post(entry["url"], headers=headers)
        if response.status_code in (200, 204):
            await self.send(json.dumps({"status": "ok", "action": command}))
        else:
            await self.send(json.dumps({"status": "error", "action": command, "code": response.status_code}))
