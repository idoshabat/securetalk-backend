from django.urls import re_path
from . import consumers
from accounts.middleware import JWTAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter

application = ProtocolTypeRouter({
    "websocket": JWTAuthMiddleware(
        URLRouter([
            re_path(r"ws/chat/(?P<username>[^/]+)/$", consumers.ChatConsumer.as_asgi()),
        ])
    ),
})
