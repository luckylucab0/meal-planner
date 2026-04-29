"""Erkennt Reste aus überzähligen Verkaufseinheiten und reicht Hinweise an den Agent.

Heuristik: für jede Zutat `min(verfügbare Pack-Grösse) - tatsächlich verbraucht`
ergibt eine Restmenge, die in den nächsten 1–2 Tagen verplant werden sollte.
Wird in Schritt 7 implementiert.
"""
