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
            await asyncio.sleep(0.00001)

    async def get_player_status(self):
        headers = {"Authorization": "Bearer " + self.access_token}
        player_url = "https://api.spotify.com/v1/me/player"
        async with httpx.AsyncClient() as client:
            response = await client.get(player_url, headers=headers)
            if response.status_code != 200:
                return None
            data = response.json()
            return {
                "current_time": data.get("progress_ms"),
                "duration": data.get("item", {}).get("duration_ms"),
                "is_playing": data.get("is_playing"),
                "currently_playing": data.get("item", {}).get("name"),
                "curent_time_min_sec": f"{data.get('progress_ms') // 60000}:{str(data.get('progress_ms') % 60000 // 1000).zfill(2)}",
            }
