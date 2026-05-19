import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from api_server.services.oauth.models import OAuthToken, OAuthUser, OAuthProvider, OAuthConfig


class OAuthService:
    def __init__(self):
        self.providers: Dict[str, OAuthConfig] = {}
        self._setup_claude_provider()

    def _setup_claude_provider(self):
        self.providers[OAuthProvider.CLAUDE] = OAuthConfig(
            client_id="",
            client_secret="",
            redirect_uri="/api/oauth/callback/claude",
            provider=OAuthProvider.CLAUDE,
            authorization_url="https://claude.ai/oauth2/v1/authorize",
            token_url="https://claude.ai/oauth2/v1/token",
            user_info_url="https://claude.ai/oauth2/v1/userinfo",
            scopes=["profile", "email"],
        )

    def get_authorization_url(self, provider: str) -> str:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.providers[provider]
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
        }

        query = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config.authorization_url}?{query}"

    async def exchange_code(self, provider: str, code: str) -> OAuthToken:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.providers[provider]

        data = {
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": config.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(config.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        return OAuthToken(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope"),
        )

    async def get_user_info(self, provider: str, access_token: str) -> OAuthUser:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.providers[provider]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config.user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            user_data = response.json()

        return OAuthUser(
            id=user_data.get("sub", user_data.get("id", "")),
            email=user_data.get("email", ""),
            name=user_data.get("name"),
            avatar_url=user_data.get("picture"),
            provider=provider,
        )

    async def refresh_token(self, provider: str, refresh_token: str) -> OAuthToken:
        if provider not in self.providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.providers[provider]

        data = {
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(config.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

        return OAuthToken(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope"),
        )

    def register_provider(self, config: OAuthConfig) -> None:
        self.providers[config.provider] = config

    def get_provider(self, provider: str) -> Optional[OAuthConfig]:
        return self.providers.get(provider)