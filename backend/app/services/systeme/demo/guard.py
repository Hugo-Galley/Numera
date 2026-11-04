"""Instance de démonstration : écritures refusées sur l'instance publique."""
from app.core.login_rate_limit import LoginRateLimiter

DEMO_STAMP_KEY = "demo_generated_on"

# Actions impossibles sur l'instance publique : identifiants, 2FA, passkeys, jetons MCP, sauvegardes,
# notifications sortantes et tout ce qui déclenche un appel réseau vers une adresse choisie par le visiteur.
# Plafonds de l'instance publique (identifiants publics, hôte partagé avec la prod) : import de 200 Ko au plus,
# 120 écritures par minute et par IP, puis blocage d'une minute (429).
DEMO_MAX_UPLOAD_BYTES = 200 * 1024
demo_write_limiter = LoginRateLimiter(max_attempts=120, window_seconds=60, lockout_seconds=60)

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


def demo_write_allowed(method: str, key: str) -> bool:
    """Compte une écriture pour `key` (IP) ; False quand le quota par fenêtre est dépassé. Les lectures sont libres."""
    if method in ("GET", "HEAD", "OPTIONS"):
        return True
    if not demo_write_limiter.is_allowed(key):
        return False
    demo_write_limiter.record_failure(key)  # « failure » = événement compté par le limiteur
    return True
