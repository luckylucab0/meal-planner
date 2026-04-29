"""Fernet-Wrapper für die Verschlüsselung sensibler Werte (z.B. CalDAV-Passwort).

Der Schlüssel kommt aus `settings.encryption_key` (Fernet-base64, 32 Bytes).
Wenn kein Key konfiguriert ist, schlagen `encrypt`/`decrypt` mit einer klaren
Domain-Exception fehl statt mit einem rohen Cryptography-Error.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.exceptions import MealPlannerError


class EncryptionNotConfiguredError(MealPlannerError):
    """Wird ausgelöst, wenn `ENCRYPTION_KEY` fehlt oder ungültig ist."""


class DecryptionError(MealPlannerError):
    """Verschlüsselter Wert konnte nicht entschlüsselt werden."""


def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise EncryptionNotConfiguredError(
            "ENCRYPTION_KEY ist nicht gesetzt — bitte in .env eintragen."
        )
    try:
        return Fernet(settings.encryption_key.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionNotConfiguredError(
            "ENCRYPTION_KEY ist kein gültiger Fernet-Key (32 Byte url-safe base64)."
        ) from exc


def encrypt(plaintext: str) -> str:
    """Verschlüsselt einen String und gibt das Ergebnis als URL-safe Base64 zurück."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Entschlüsselt einen mit `encrypt` erzeugten String."""
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise DecryptionError("Token konnte nicht entschlüsselt werden.") from exc
