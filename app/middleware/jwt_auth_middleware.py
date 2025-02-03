from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model


User = get_user_model()


@database_sync_to_async
def get_user(token):
    try:
        validated_token = AccessToken(token)
        user_id = validated_token['user_id']
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()
    except Exception as e:
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)

        headers = {key.lower(): value for key, value in dict(scope['headers']).items()}
        token = None

        auth_header = headers.get(b'authorization', None)
        if auth_header:
            try:
                token = auth_header.decode().split(' ')[1]
            except IndexError:
                token = None

        if token:
            scope['user'] = await get_user(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
