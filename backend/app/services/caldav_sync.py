"""CalDAV-Sync mit Apple iCloud (App-spezifisches Passwort).

Liest verschlüsselte Credentials aus `app_settings`, legt einen Kalender
mit konfigurierbarem Namen an (default „Meal Plan") und schreibt Events
idempotent (UID = `meal-{plan_id}-{meal_id}`).

Wird in Schritt 12 implementiert.
"""
