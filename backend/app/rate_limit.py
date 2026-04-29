"""Rate-Limiter-Instanz für die gesamte Applikation.

Greift pro Source-IP. Im Single-Host-LAN-Modell dient das Limit primär
als Notbremse gegen versehentliche oder in Schleife laufende Anfragen —
nicht als Ersatz für Authentifizierung. Wird in `main.py` an die App
gebunden und in `api/plans.py` auf die teuren Agent-Endpoints angewendet.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
