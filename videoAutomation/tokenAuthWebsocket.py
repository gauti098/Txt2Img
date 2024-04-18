from channels.auth import AuthMiddlewareStack
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user(token):
    try:
        return Token.objects.get(key=token).user
    except Token.DoesNotExist:
        return AnonymousUser()
        
class QueryAuthMiddleware:
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        headers = scope['query_string'].split(b'token=')
        if len(headers)>=2:
            maintoken = headers[1].split(b'&')[0]
            try:
                scope['user'] = await get_user(maintoken.decode())
            except:
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        return await self.app(scope, receive, send)

TokenAuthMiddlewareStack = lambda inner: QueryAuthMiddleware(AuthMiddlewareStack(inner))   
