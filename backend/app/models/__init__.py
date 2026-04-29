"""Re-Export aller ORM-Modelle.

Wichtig für Alembic-Autogenerate: dieses Modul importiert sämtliche Tabellen,
sodass `Base.metadata` vollständig befüllt ist, sobald irgendetwas aus
`app.models` importiert wird.
"""

from app.database import Base
from app.models.app_settings import AppSettings
from app.models.meal_history import MealHistory
from app.models.meal_plan import Meal, MealIngredient, MealPlan
from app.models.preferences import UserPreferences
from app.models.product import Product

__all__ = [
    "AppSettings",
    "Base",
    "Meal",
    "MealHistory",
    "MealIngredient",
    "MealPlan",
    "Product",
    "UserPreferences",
]
