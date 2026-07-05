# -*- coding: utf-8 -*-
"""
app.py — Point d'entrée de l'application.

L'ancien app.py (673 lignes) contenait tout : config, connexion DB, auth,
CRUD mangas, galerie communautaire, exports... Il a été découpé en modules
pour être plus facile à maintenir :

    core.py              -> instance Flask, config, constantes
    db.py                -> connexion PostgreSQL + création/migration du schéma
    helpers.py           -> fonctions partagées (validation, enrichissement...)
    routes_auth.py       -> /register /login /logout
    routes_mangas.py     -> CRUD mangas, pagination, stats, exports
    routes_community.py  -> /galerie, top3, commentaires, copie de fiches
    routes_collections.py-> collections personnalisées (nouveau)
    routes_rappels.py    -> rappels de lecture (nouveau)

Chaque module de routes utilise @app.route(...) directement sur l'instance
partagée définie dans core.py (pas de Blueprints), donc tous les noms
d'endpoints (index, login, galerie, ...) et tous les url_for(...) déjà
présents dans les templates restent valides sans aucune modification.
"""
import os

from core import app          # noqa: F401  (instance Flask partagée)
from db import init_db

# L'import de chaque module de routes a pour effet de bord d'enregistrer
# ses routes sur `app` grace aux décorateurs @app.route(...).
import routes_auth        # noqa: F401,E402
import routes_mangas       # noqa: F401,E402
import routes_community    # noqa: F401,E402
import routes_collections  # noqa: F401,E402
import routes_rappels      # noqa: F401,E402

# Schéma de base de données : créé/migré une seule fois au démarrage
# (avant, c'était refait à chaque requête sur / et /galerie).
try:
    init_db()
except Exception as e:
    # On ne bloque pas le démarrage si la DB n'est pas encore joignable
    # (utile en développement local), mais on le signale clairement.
    print(f"[avertissement] init_db() a échoué au démarrage : {e}")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
