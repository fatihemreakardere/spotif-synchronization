from django.urls import re_path
from .consumers import SpotifyPlayerConsumer

websocket_urlpatterns = [
    re_path(r'^ws/sync/$', SpotifyPlayerConsumer.as_asgi()),
]
