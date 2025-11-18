# core/asgi.py
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Django ASGI application
django_asgi_app = get_asgi_application()

import accounts.routing  # your websocket routes

def get_application():
    # delayed import to avoid AppRegistryNotReady
    from accounts.middleware import JWTAuthMiddleware
    
    return ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(
            URLRouter(
                accounts.routing.websocket_urlpatterns
            )
        ),
    })

application = get_application()
