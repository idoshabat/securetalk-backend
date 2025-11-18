# yourapp/middleware.py
import urllib
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware

@database_sync_to_async
def get_user_from_token(validated_token):
    from django.contrib.auth import get_user_model  # ✅ delayed import
    User = get_user_model()
    try:
        user_id = validated_token['user_id']
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT auth over WebSocket using query string token.
    """
    async def __call__(self, scope, receive, send):
        # Delayed imports to avoid AppRegistryNotReady
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        # Get the token from query string
        query_string = scope.get('query_string', b'').decode()
        qs = urllib.parse.parse_qs(query_string)
        token_list = qs.get('token')

        if token_list:
            token = token_list[0]  # get the first token
            try:
                validated_token = UntypedToken(token)  # validate JWT
                scope['user'] = await get_user_from_token(validated_token)
            except (InvalidToken, TokenError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
