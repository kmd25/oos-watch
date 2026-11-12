"""Tests for the login check. No network and no Clerk: the tests make their own key pair,
sign tokens with the private key, and hand the app the public key."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from api import auth
from api.main import app, get_conn, get_dot_number

ISSUER = "https://clerk.example.test"
SITE = "https://app.example.test"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(key=PRIVATE_KEY, **changes):
    now = int(time.time())
    claims = {"sub": "user_1", "iss": ISSUER, "azp": SITE, "nbf": now - 5, "exp": now + 60, **changes}
    return jwt.encode(claims, key, algorithm="RS256")


def get(client, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/whoami", headers=headers)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CLERK_ISSUER", ISSUER)
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", SITE)
    monkeypatch.setattr(auth, "signing_key", lambda token: PRIVATE_KEY.public_key())
    return TestClient(app)


def test_no_token_is_refused(client):
    assert get(client).status_code == 401


def test_a_valid_token_is_accepted(client):
    response = get(client, make_token())

    assert response.status_code == 200
    assert response.json() == {"user_id": "user_1", "organization_id": None}


def test_the_active_organization_is_read_from_the_token(client):
    response = get(client, make_token(o={"id": "org_1", "rol": "admin"}))

    assert response.json() == {"user_id": "user_1", "organization_id": "org_1"}


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        make_token(key=OTHER_KEY),  # signed by someone else
        make_token(exp=int(time.time()) - 60),  # expired
        make_token(iss="https://clerk.someone-else.test"),  # another Clerk application
        make_token(azp="https://evil.example.test"),  # made for another website
    ],
    ids=["garbage", "wrong key", "expired", "wrong issuer", "wrong site"],
)
def test_a_bad_token_is_refused(client, token):
    assert get(client, token).status_code == 401


def test_data_endpoints_need_a_login(client):
    for path in ["/summary", "/inspections", "/violations/top", "/trends", "/crashes"]:
        assert client.get(path).status_code == 401
