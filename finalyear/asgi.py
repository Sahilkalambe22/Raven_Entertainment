"""
ASGI config for finalyear project.

This handles both HTTP and WebSocket connections using Django Channels.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import your websocket routing
import user.routing  # make sure you have this file

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finalyear.settings")

# Create the Django ASGI application early to avoid AppRegistryNotReady errors
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # HTTP requests will be handled by Django
    "http": django_asgi_app,

    # WebSocket requests will be handled by Channels
    "websocket": AuthMiddlewareStack(
        URLRouter(
            user.routing.websocket_urlpatterns
        )
    ),
})
