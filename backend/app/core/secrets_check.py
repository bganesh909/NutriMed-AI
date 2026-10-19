"""
Refuse to run in production with placeholder or weak secrets.

JWT_SECRET signs every session token: anyone who knows it can mint a token for
any user, admins included. AES_KEY encrypts uploaded lab reports at rest. Both
ship with placeholder defaults so the app runs out of the box in development;
in production (DEBUG off) the API will not start until they are replaced.

The result is deliberately not exposed on an HTTP endpoint: announcing "this
deployment uses the default JWT_SECRET" would tell an attacker exactly how to
forge an admin session.
"""

import logging

logger = logging.getLogger("nutrimed.security")

MIN_SECRET_LENGTH = 32

# Substrings of the placeholder values used in this repository (config
# defaults, .env.example, docs/DEPLOYMENT.md, test settings). A generated
# secret never contains them.
_PLACEHOLDER_MARKERS = (
    "change-me",
    "change-in-production",
    "changeme",
    "your-",
    "generate_a",
    "placeholder",
    "secret-key",
    "example",
    "test-",
)

GENERATE_HINT = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'


class InsecureSecretsError(RuntimeError):
    """Raised at startup when production secrets are placeholders or weak."""


def secret_problems(settings) -> list[str]:
    """What is wrong with JWT_SECRET and AES_KEY; empty when both look sound."""
    problems: list[str] = []
    for name in ("JWT_SECRET", "AES_KEY"):
        value = getattr(settings, name, "") or ""
        lowered = value.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
            problems.append(f"{name} is a placeholder value")
        elif len(value) < MIN_SECRET_LENGTH:
            problems.append(f"{name} is shorter than {MIN_SECRET_LENGTH} characters")
        elif len(set(value)) < 10:
            problems.append(f"{name} is too repetitive to be a random secret")
    if settings.JWT_SECRET and settings.JWT_SECRET == settings.AES_KEY:
        problems.append("JWT_SECRET and AES_KEY must be different values")
    return problems


def enforce_secrets(settings) -> None:
    """
    Raise InsecureSecretsError if the secrets are unsafe and DEBUG is off.
    With DEBUG on (local development) log a warning and carry on.
    """
    problems = secret_problems(settings)
    if not problems:
        return

    if settings.DEBUG:
        logger.warning(
            "Insecure secrets, allowed only because DEBUG=true (never in production): %s",
            "; ".join(problems),
        )
        return

    raise InsecureSecretsError(
        "Refusing to start: insecure secrets.\n"
        + "".join(f"  - {p}\n" for p in problems)
        + f"Generate each value with:  {GENERATE_HINT}\n"
        "and set JWT_SECRET and AES_KEY in the environment (.env). Keep the AES_KEY "
        "that encrypted existing uploads, or those reports become unreadable.\n"
        "For local development only, set DEBUG=true to run with the placeholders."
    )
