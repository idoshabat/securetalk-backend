# import os
# import django
# from channels.routing import ProtocolTypeRouter, URLRouter
# from django.core.asgi import get_asgi_application
# from channels.auth import AuthMiddlewareStack

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# # Setup Django first
# django.setup()

# # Delay import until after setup
# from accounts import routing as accounts_routing

# # Create the application
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             accounts_routing.websocket_urlpatterns
#         )
#     ),
# })
