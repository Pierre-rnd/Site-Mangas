# -*- coding: utf-8 -*-
"""
helpers.py — Fonctions partagées entre les différents modules de routes.

Contient aussi des petits helpers de validation qui remplacent les anciens
accès directs request.form['xxx'] (qui plantaient avec une erreur 500 brute
si le champ était absent du formulaire).
"""
from datetime import datetime

import cloudinary.uploader
from db import db_cursor

from core import COLLECTION_COLORS


# ── Chargement des mangas ───────────────────────────────────────────────────
def charger_mangas(user_id):
    with db_cursor(dict_cursor=True) as cur:
        cur.execute("SELECT * FROM mangas WHERE user_id = %s", (user_id,))
        mangas = cur.fetchall()
    for m in mangas:
        g = m.get('genres') or ''
        m['genres'] = [x.strip() for x in g.split(',') if x.strip()]
    return mangas


def upload_image_cloudinary(file):
    """Upload un fichier vers Cloudinary et renvoie l'URL sécurisée."""
    result = cloudinary.uploader.upload(
        file,
        folder="manga_covers",
        transformation=[{"width": 400, "height": 570, "crop": "fill", "quality": "auto", "fetch_format": "auto"}]
    )
    return result.get("secure_url")


def enrich_mangas(mangas):
    """Ajoute les champs calculés : fini (bool), non_lu, last_read_label."""
    for manga in mangas:
        manga['fini'] = str(manga.get('fini')).lower() == 'true'
        dl = manga.get('derniere_lecture')
        if dl:
            try:
                date_lecture = datetime.strptime(str(dl), '%Y-%m-%d').date()
                delta = datetime.now().date() - date_lecture
                manga['jours_depuis_lecture'] = delta.days
                manga['non_lu'] = (delta.days >= 7 and not manga['fini'])
                if delta.days == 0:
                    manga['last_read_label'] = "Lu aujourd'hui"
                elif delta.days == 1:
                    manga['last_read_label'] = "Lu hier"
                else:
                    manga['last_read_label'] = f"Lu il y a {delta.days} jours"
            except Exception:
                manga['non_lu'] = False
                manga['jours_depuis_lecture'] = None
                manga['last_read_label'] = "—"
        else:
            manga['non_lu'] = False
            manga['jours_depuis_lecture'] = None
            manga['last_read_label'] = "Jamais lu"
    return mangas


def attach_collections(mangas, user_id):
    """Attache à chaque manga la liste de ses collections ([{id, nom, couleur}])."""
    if not mangas:
        return mangas
    with db_cursor(dict_cursor=True) as cur:
        cur.execute(
            "SELECT mc.manga_id, c.id, c.nom, c.couleur FROM manga_collections mc"
            " JOIN collections c ON c.id = mc.collection_id"
            " WHERE c.user_id = %s",
            (user_id,)
        )
        rows = cur.fetchall()
    by_manga = {}
    for r in rows:
        by_manga.setdefault(r['manga_id'], []).append(
            {"id": r['id'], "nom": r['nom'], "couleur": r['couleur']}
        )
    for m in mangas:
        m['collections'] = by_manga.get(m['id'], [])
    return mangas


def get_user_collections(user_id):
    with db_cursor(dict_cursor=True) as cur:
        cur.execute(
            "SELECT id, nom, couleur FROM collections WHERE user_id = %s ORDER BY nom",
            (user_id,)
        )
        return cur.fetchall()


def next_collection_color(user_id):
    """Choisit une couleur de la palette en fonction du nombre de collections
    déjà créées, pour varier automatiquement les couleurs."""
    count = len(get_user_collections(user_id))
    return COLLECTION_COLORS[count % len(COLLECTION_COLORS)]


# ── Rappels de lecture ──────────────────────────────────────────────────────
def get_rappel_jours(user_id):
    with db_cursor(dict_cursor=True) as cur:
        cur.execute("SELECT rappel_jours FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    return (row or {}).get('rappel_jours') or 7


def count_mangas_a_relancer(user_id):
    """Nombre de mangas non terminés dont la dernière lecture dépasse le seuil
    de rappel de l'utilisateur (ou jamais lus)."""
    seuil = get_rappel_jours(user_id)
    mangas = enrich_mangas(charger_mangas(user_id))
    count = 0
    for m in mangas:
        if m['fini']:
            continue
        if m.get('derniere_lecture') is None:
            count += 1
        elif m.get('jours_depuis_lecture') is not None and m['jours_depuis_lecture'] >= seuil:
            count += 1
    return count


# ── Validation de formulaire ────────────────────────────────────────────────
def form_str(form, field, default=''):
    return (form.get(field, default) or default).strip()


def form_int(form, field, default=0, min_value=None, max_value=None):
    """Convertit un champ de formulaire en int en toute sécurité (jamais de
    ValueError qui ferait planter la requête)."""
    raw = form.get(field, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value


def form_bool_oui_non(form, field, default=False):
    return form.get(field, 'oui' if default else 'non') == 'oui'


def paginate(items, page, per_page):
    """Découpe une liste déjà triée/filtrée en pages.
    Renvoie (page_items, total_pages, page) avec page toujours valide."""
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages, page
