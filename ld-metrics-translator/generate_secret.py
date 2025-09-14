#!/usr/bin/env python3
"""Generate a secure secret key for Flask application."""

import secrets

def generate_secret_key():
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(32)

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print(f"Generated Secret Key: {secret_key}")
    print(f"\nAdd this to your app.yaml:")
    print(f'  SECRET_KEY: "{secret_key}"')
