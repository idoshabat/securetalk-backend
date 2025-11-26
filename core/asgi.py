import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from accounts.routing import websocket_urlpatterns  # <-- IMPORTANT
from accounts.middleware import JWTAuthMiddleware  # <-- Add this

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),

    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(  # <-- use your JWT middleware here
            URLRouter(websocket_urlpatterns)
        )
    ),
})
