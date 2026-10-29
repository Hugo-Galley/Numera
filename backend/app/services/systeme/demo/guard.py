"""Instance de démonstration : écritures refusées sur l'instance publique."""

DEMO_STAMP_KEY = "demo_generated_on"

# Actions impossibles sur l'instance publique : identifiants, 2FA, passkeys, jetons MCP, sauvegardes,
# notifications sortantes et tout ce qui déclenche un appel réseau vers une adresse choisie par le visiteur.
_DEMO_BLOCKED_PREFIXES = ("/admin/", "/notifications/", "/logos/")
_DEMO_BLOCKED_SUFFIXES = ("/refresh", "/refresh-held", "/auto-decompose")


def is_blocked_in_demo(method: str, path: str) -> bool:
    if method in ("GET", "HEAD", "OPTIONS"):
        return False
    if path.startswith(_DEMO_BLOCKED_PREFIXES):
        return True
    if path.startswith("/auth/totp/") and path != "/auth/totp/login":
        return True
    if path.startswith("/auth/passkey") and not path.startswith("/auth/passkey/login/"):
        return True
    return path.startswith("/etf-profiles/") and path.endswith(_DEMO_BLOCKED_SUFFIXES)
