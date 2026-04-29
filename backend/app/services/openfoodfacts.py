"""Open-Food-Facts-Client — schlägt Zutaten in `world.openfoodfacts.org` nach.

Cache-Strategie: Lookup zuerst in lokaler `products`-Tabelle (Treffer auf
normalisierten Namen). Bei Miss → OFF-Search-API → Top-Treffer in DB
übernehmen. Pflicht-User-Agent laut OFF-Policy.

Wird in Schritt 5 implementiert.
"""
