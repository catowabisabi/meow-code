from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    token_type: str = "Bearer"
    scope: Optional[str] = None


@dataclass
class OAuthUser:
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    provider: str


class OAuthProvider:
    CLAUDE = "claude"
    GITHUB = "github"
    GOOGLE = "google"


class OAuthConfig:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        provider: str,
        authorization_url: str,
        token_url: str,
        user_info_url: str,
        scopes: Optional[list[str]] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.provider = provider
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.user_info_url = user_info_url
        self.scopes = scopes or []