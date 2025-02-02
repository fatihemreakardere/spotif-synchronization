from django.urls import path
from .consumers import SpotifyPlayerConsumer

websocket_urlpatterns = [
    path('ws/sync/', SpotifyPlayerConsumer.as_asgi()),
]
