"""Claude-Agent — Tool-Use-Loop zur Wochenplan-Generierung.

System-Prompt mit Schweizer Kontext (CHF-Preise, Saisonalität, typisches
Migros/Coop-Sortiment), Prompt-Caching für stabile Teile, Multi-Turn-Loop
mit den Tools `get_user_preferences`, `get_recent_meal_history`,
`lookup_product`, `upsert_product`, `calculate_nutrition`, `save_meal_plan`.

Wird in Schritten 6/7 implementiert.
"""
