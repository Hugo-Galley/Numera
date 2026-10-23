"""Passkeys WebAuthn : un authentificateur logiciel (clé EC P-256, attestation « none ») signe de vrais défis."""
import base64
import hashlib
import json
import os

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from app.core.config import settings

ORIGIN = "http://localhost:5173"
RP_ID = "localhost"
CRED_ID = os.urandom(16)


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class SoftAuthenticator:
    def __init__(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.sign_count = 0

    def _client_data(self, kind: str, challenge: str) -> bytes:
        return json.dumps({"type": kind, "challenge": challenge, "origin": ORIGIN, "crossOrigin": False}).encode()

    def register(self, options: dict) -> dict:
        nums = self.key.public_key().public_numbers()
        cose = cbor2.dumps({1: 2, 3: -7, -1: 1, -2: nums.x.to_bytes(32, "big"), -3: nums.y.to_bytes(32, "big")})
        auth_data = (
            hashlib.sha256(RP_ID.encode()).digest() + bytes([0x45]) + (0).to_bytes(4, "big")
            + bytes(16) + len(CRED_ID).to_bytes(2, "big") + CRED_ID + cose
        )
        client = self._client_data("webauthn.create", options["challenge"])
        return {
            "id": b64(CRED_ID), "rawId": b64(CRED_ID), "type": "public-key",
            "response": {
                "clientDataJSON": b64(client),
                "attestationObject": b64(cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})),
            },
        }

    def assertion(self, options: dict, key: ec.EllipticCurvePrivateKey | None = None) -> dict:
        self.sign_count += 1
        auth_data = hashlib.sha256(RP_ID.encode()).digest() + bytes([0x05]) + self.sign_count.to_bytes(4, "big")
        client = self._client_data("webauthn.get", options["challenge"])
        signature = (key or self.key).sign(auth_data + hashlib.sha256(client).digest(), ec.ECDSA(hashes.SHA256()))
        return {
            "id": b64(CRED_ID), "rawId": b64(CRED_ID), "type": "public-key",
            "response": {"clientDataJSON": b64(client), "authenticatorData": b64(auth_data), "signature": b64(signature)},
        }


def _register(client, authenticator):
    headers = {"Origin": ORIGIN}
    opts = client.post("/auth/passkey/register/options", headers=headers).json()
    resp = client.post(
        "/auth/passkey/register/verify",
        headers=headers,
        json={"state": opts["state"], "credential": authenticator.register(opts["options"]), "name": "iPhone"},
    )
    return resp


def test_register_then_login_with_passkey(client):
    assert settings.ADMIN_USERNAME  # garde-fou : le jeton émis porte l'identifiant admin
    assert client.get("/auth/passkey/available").json() == {"available": False}
    authenticator = SoftAuthenticator()
    assert _register(client, authenticator).status_code == 200
    assert client.get("/auth/passkey/available").json() == {"available": True}
    assert client.get("/auth/passkey").json()[0]["name"] == "iPhone"

    headers = {"Origin": ORIGIN}
    opts = client.post("/auth/passkey/login/options", headers=headers).json()
    resp = client.post(
        "/auth/passkey/login/verify",
        headers=headers,
        json={"state": opts["state"], "credential": authenticator.assertion(opts["options"])},
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"


def test_login_refused_with_foreign_key(client):
    authenticator = SoftAuthenticator()
    assert _register(client, authenticator).status_code == 200
    headers = {"Origin": ORIGIN}
    opts = client.post("/auth/passkey/login/options", headers=headers).json()
    forged = authenticator.assertion(opts["options"], key=ec.generate_private_key(ec.SECP256R1()))
    resp = client.post("/auth/passkey/login/verify", headers=headers, json={"state": opts["state"], "credential": forged})
    assert resp.status_code == 401


def test_origin_must_be_allowed(client):
    resp = client.post("/auth/passkey/register/options", headers={"Origin": "https://evil.example"})
    assert resp.status_code == 400
    assert client.post("/auth/passkey/login/options").status_code == 400


def test_login_options_without_passkey(client):
    assert client.post("/auth/passkey/login/options", headers={"Origin": ORIGIN}).status_code == 404


def test_delete_passkey(client):
    authenticator = SoftAuthenticator()
    credential_id = _register(client, authenticator).json()["id"]
    assert client.delete(f"/auth/passkey/{credential_id}").status_code == 200
    assert client.get("/auth/passkey").json() == []
