import traceback
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, InvalidToken
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_key):
    try:
        # Validate the token
        token = AccessToken(token_key)
        # Get the user ID from the token payload
        user_id = token.payload['user_id']
        # Fetch the user from the database
        return User.objects.get(id=user_id)
    except (InvalidToken, User.DoesNotExist):
        # Return an anonymous user if token is invalid or user doesn't exist
        return AnonymousUser()
    except Exception as e:
        print(f"An unexpected error occurred during token authentication: {e}")
        traceback.print_exc()
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Custom WebSocket authentication middleware that uses JWT tokens.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Get the query string from the scope
        query_string = scope.get("query_string", b"").decode("utf-8")
        
        # Parse the query string to get the token
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        if token:
            # If a token is found, authenticate the user
            scope['user'] = await get_user_from_token(token)
        else:
            # If no token, the user is anonymous
            scope['user'] = AnonymousUser()
            
        return await self.inner(scope, receive, send)

