"""Check that a request comes from a signed-in user.

The browser signs in with Clerk and gets a short-lived session token: a JWT, which is
a small piece of JSON plus a signature. Clerk signs it with a private key only Clerk has
and publishes the matching public keys, so we can check a token is genuine without
calling Clerk on every request.
"""

import os
from functools import cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Reads "Authorization: Bearer <token>" from the request. auto_error=False lets us
# answer a missing header ourselves, with the same 401 as a bad token.
bearer = HTTPBearer(auto_error=False)


@cache
def jwks_client():
    """Fetches Clerk's public keys once and remembers them (JWKS = JSON Web Key Set)."""
    return jwt.PyJWKClient(f"{os.environ['CLERK_ISSUER']}/.well-known/jwks.json")


def signing_key(token):
    """The public key that matches the key ID written in the token's header."""
    return jwks_client().get_signing_key_from_jwt(token).key


def get_claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """Return the verified contents ("claims") of the session token, or refuse with 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    token = credentials.credentials
    try:
        claims = jwt.decode(
            token,
            signing_key(token),
            # Name the algorithm ourselves; never trust the one the token asks for.
            algorithms=["RS256"],
            # Must have been issued by our Clerk application, not somebody else's.
            issuer=os.environ["CLERK_ISSUER"],
            # decode() also rejects tokens that have expired (exp) or are not valid yet (nbf).
            options={"require": ["exp", "nbf", "sub"]},
            leeway=10,  # seconds of tolerance for clocks that disagree slightly
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from None

    # azp ("authorized party") is the website the token was created for. Refusing other
    # sites stops a token made for a different app from being used against ours.
    allowed = os.environ["CLERK_AUTHORIZED_PARTIES"].split(",")
    if "azp" in claims and claims["azp"] not in allowed:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return claims
