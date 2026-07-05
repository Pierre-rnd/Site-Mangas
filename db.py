# -*- coding: utf-8 -*-
"""
db.py — Connexion PostgreSQL et création/migration du schéma.

Avant : ensure_genres_column() et ensure_community_tables() étaient
ré-exécutées à CHAQUE requête (à chaque chargement de mangas, à chaque visite
de /galerie). C'est inutile et ça ralentit chaque page pour rien.
Maintenant : init_db() est appelée UNE SEULE FOIS au démarrage (voir app.py).
"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn


@contextmanager
def db_cursor(dict_cursor=False, commit=False):
    """Context manager qui garantit la fermeture propre du curseur/connexion
    même en cas d'exception, et le rollback automatique en cas d'erreur.

    Usage:
        with db_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM mangas WHERE id = %s", (id,))
            row = cur.fetchone()
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if dict_cursor else conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def init_db():
    """Crée/migre toutes les tables et colonnes nécessaires. Appelée une
    seule fois au démarrage de l'application (idempotent grâce à IF NOT EXISTS)."""
    with db_cursor(commit=True) as cur:
        # Colonne genres sur mangas (ajoutée après coup dans les versions précédentes)
        cur.execute("ALTER TABLE mangas ADD COLUMN IF NOT EXISTS genres TEXT DEFAULT '';")

        # Seuil de rappel de lecture personnalisable par utilisateur
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS rappel_jours INTEGER DEFAULT 7;"
        )

        # Communauté : top3 et commentaires
        cur.execute("""
            CREATE TABLE IF NOT EXISTS top3 (
                user_id  INTEGER NOT NULL,
                manga_id INTEGER NOT NULL,
                rank     SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 3),
                PRIMARY KEY (user_id, rank)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS commentaires (
                id         SERIAL PRIMARY KEY,
                manga_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                texte      TEXT NOT NULL,
                created_at DATE NOT NULL DEFAULT CURRENT_DATE
            );
        """)

        # Collections personnalisées (nouvelle fonctionnalité)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id         SERIAL PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                nom        TEXT NOT NULL,
                couleur    TEXT DEFAULT '#7c5cff',
                created_at DATE NOT NULL DEFAULT CURRENT_DATE,
                UNIQUE (user_id, nom)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS manga_collections (
                manga_id      INTEGER NOT NULL,
                collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
                PRIMARY KEY (manga_id, collection_id)
            );
        """)
