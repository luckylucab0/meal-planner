"""Domain-spezifische Exception-Klassen.

Wird im Verlauf der Implementierung pro Modul erweitert.
"""


class MealPlannerError(Exception):
    """Basis-Klasse für alle Meal-Planner-Fehler."""


class AgentPlanningError(MealPlannerError):
    """Wird ausgelöst, wenn der Claude-Agent keinen validen Plan erzeugen kann."""


class OpenFoodFactsError(MealPlannerError):
    """Fehler beim Abrufen oder Parsen von Open-Food-Facts-Daten."""


class CalDavSyncError(MealPlannerError):
    """Fehler beim Synchronisieren mit dem CalDAV-Server."""
