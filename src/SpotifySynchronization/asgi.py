"""
ASGI config for SpotifySynchronization project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import music.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SpotifySynchronization.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(music.routing.websocket_urlpatterns),
})
