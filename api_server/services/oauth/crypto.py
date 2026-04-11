"""PKCE (Proof Key for Code Exchange) cryptographic functions."""

import base64
import hashlib
import secrets


def _base64url_encode(buffer: bytes) -> str:
    """Encode bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(buffer).rstrip(b"=").decode()


def generate_code_verifier() -> str:
    """
    Generate a random PKCE code verifier.
    
    The code verifier is a high-entropy cryptographic random string using
    unreserved URL characters ([A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~").
    """
    return _base64url_encode(secrets.token_bytes(32))


def generate_code_challenge(verifier: str) -> str:
    """
    Generate a PKCE code challenge from a code verifier using S256 method.
    
    The code challenge is a base64url-encoded SHA256 hash of the verifier.
    """
    hash_obj = hashlib.sha256()
    hash_obj.update(verifier.encode())
    return _base64url_encode(hash_obj.digest())


def generate_state() -> str:
    """
    Generate a random state parameter for OAuth CSRF protection.
    
    The state is a base64url-encoded random value used to prevent CSRF attacks.
    """
    return _base64url_encode(secrets.token_bytes(32))
