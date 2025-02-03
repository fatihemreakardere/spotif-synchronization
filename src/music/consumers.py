import asyncio
import httpx
import urllib.parse
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SpotifyPlayerConsumer(AsyncWebsocketConsumer):
    channel_layer_alias = "default"  # added: override default channel layer reference

    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = urllib.parse.parse_qs(query_string)
        token_pair = params.get("token")
        self.access_token = token_pair[0] if token_pair else None
        
        self.party = params.get("party", [None])[0]
        if not self.access_token or not self.party:
            await self.close()
        else:
            await self.accept()
            # Send self connection id to client
            await self.send(text_data=json.dumps({"self_id": self.channel_name}))
            # Add to party group:
            self.group_name = "party_" + self.party
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            self.loop_task = asyncio.create_task(self.player_loop())

    async def disconnect(self, close_code):
        if hasattr(self, "loop_task"):
            self.loop_task.cancel()
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def player_loop(self):
        while True:
            status = await self.get_player_status()
            if status:
                # Include unique connection id so clients can update participant status:
                status["connection_id"] = self.channel_name
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "participant_status", "status": status}
                )
            await asyncio.sleep(2)

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
                # New field – track URI (needed for syncing):
                "track_uri": data.get("item", {}).get("uri", ""),
                "curent_time_min_sec": f"{data.get('progress_ms') // 60000}:{str(data.get('progress_ms') % 60000 // 1000).zfill(2)}",
            }


    async def participant_status(self, event):
        await self.send(text_data=json.dumps(event["status"]))

    async def receive(self, text_data=None):
        data = json.loads(text_data)
        command = data.get("command")
        if command == "sync":
            # Extract track info from the sync command
            track_uri = data.get("track_uri")
            position_ms = data.get("position_ms")
            if track_uri and position_ms is not None:
                await self.sync_playback(track_uri, position_ms)
            else:
                await self.send(json.dumps({"status": "error", "message": "Missing sync parameters"}))
            return
        elif command:
            # Handle existing commands (play, pause, next, previous)
            await self.control_playback(command)

    async def sync_playback(self, track_uri, position_ms):
        """
        Calls Spotify's API to set playback to a given track at a specified position.
        """
        url = "https://api.spotify.com/v1/me/player/play"
        headers = {
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json"
        }
        # The Spotify API allows passing a JSON payload with track URIs and the start position.
        body = {
            "uris": [track_uri],
            "position_ms": position_ms
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=body)
        if response.status_code in (200, 204):
            await self.send(json.dumps({"status": "ok", "action": "sync"}))
        else:
            await self.send(json.dumps({
                "status": "error",
                "action": "sync",
                "code": response.status_code,
                "message": response.text
            }))

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
