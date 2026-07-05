# -*- coding: utf-8 -*-
"""routes_mangas.py — CRUD des mangas de l'utilisateur, statistiques, exports."""
import csv
import json
from datetime import datetime
from io import StringIO

from flask import render_template, request, redirect, url_for, jsonify, Response, session

from core import app, GENRES_DISPONIBLES, PER_PAGE
from db import db_cursor
from helpers import (
    charger_mangas, enrich_mangas, upload_image_cloudinary, attach_collections,
    get_user_collections, form_str, form_int, form_bool_oui_non, paginate,
)


# ── Index ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    mangas = attach_collections(enrich_mangas(charger_mangas(session['user_id'])), session['user_id'])

    search = request.args.get('search', '').lower()
    filter_fini = request.args.get('filter_fini', '')
    filter_note = request.args.get('filter_note', '')
    filter_non_lu = request.args.get('non_lu', '') == '1'
    filter_genre = request.args.get('filter_genre', '')
    filter_collection = request.args.get('filter_collection', '')
    sort_by = request.args.get('sort', 'nom')
    order = request.args.get('order', 'asc' if sort_by == 'nom' else 'desc')
    page = form_int(request.args, 'page', default=1, min_value=1)

    if filter_fini == 'oui':
        filter_fini_value = True
    elif filter_fini == 'non':
        filter_fini_value = False
    else:
        filter_fini_value = None

    def has_collection(m):
        if not filter_collection:
            return True
        return any(c['nom'] == filter_collection for c in m.get('collections', []))

    filtered_mangas = [
        m for m in mangas
        if (search in m['nom'].lower() or search == '')
        and (filter_fini_value is None or m['fini'] == filter_fini_value)
        and (filter_note == '' or m['note'] == int(filter_note))
        and (not filter_non_lu or m.get('non_lu'))
        and (filter_genre == '' or filter_genre in m.get('genres', []))
        and has_collection(m)
    ]

    reverse = order == 'desc'
    if sort_by == 'note':
        filtered_mangas.sort(key=lambda m: int(m.get('note', 0)), reverse=reverse)
    elif sort_by == 'derniere_lecture':
        def _date_key(m):
            d = m.get('derniere_lecture')
            if d is None:
                return datetime.min.date()
            try:
                return datetime.strptime(str(d), '%Y-%m-%d').date() if isinstance(d, str) else d
            except Exception:
                return datetime.min.date()
        filtered_mangas.sort(key=_date_key, reverse=reverse)
    elif sort_by == 'chapitre':
        filtered_mangas.sort(key=lambda m: int(m.get('chapitre', 0) or 0), reverse=reverse)
    else:
        filtered_mangas.sort(key=lambda m: m['nom'].lower(), reverse=reverse)

    total_resultats = len(filtered_mangas)
    page_mangas, total_pages, page = paginate(filtered_mangas, page, PER_PAGE)

    return render_template(
        'index.html', mangas=page_mangas, sort=sort_by, order=order,
        genres_disponibles=GENRES_DISPONIBLES, filter_genre=filter_genre,
        collections_disponibles=get_user_collections(session['user_id']),
        filter_collection=filter_collection,
        page=page, total_pages=total_pages, total_resultats=total_resultats,
    )


# ── Ajouter ────────────────────────────────────────────────────────────────
@app.route('/ajouter', methods=['POST'])
def ajouter():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    image_file = request.files.get('image_file')
    if image_file and image_file.filename:
        image_url = upload_image_cloudinary(image_file)
    else:
        image_url = form_str(request.form, 'image')

    nom = form_str(request.form, 'nom')
    if not nom:
        return redirect(url_for('index'))

    genres_str = ', '.join(request.form.getlist('genres'))

    with db_cursor(dict_cursor=True, commit=True) as cur:
        cur.execute('''
            INSERT INTO mangas (nom, chapitre, saison, fini, lien, note, image, user_id, genres)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        ''', (
            nom,
            form_int(request.form, 'chapitre', default=1, min_value=0),
            form_int(request.form, 'saison', default=1, min_value=0),
            form_bool_oui_non(request.form, 'fini'),
            form_str(request.form, 'lien'),
            form_int(request.form, 'note', default=0, min_value=0, max_value=5),
            image_url,
            session['user_id'],
            genres_str
        ))
        new_id = cur.fetchone()['id']

    collection_ids = [int(x) for x in request.form.getlist('collections') if x.isdigit()]
    if collection_ids:
        with db_cursor(commit=True) as cur:
            for cid in collection_ids:
                cur.execute(
                    "INSERT INTO manga_collections (manga_id, collection_id)"
                    " SELECT %s, id FROM collections WHERE id = %s AND user_id = %s"
                    " ON CONFLICT DO NOTHING",
                    (new_id, cid, session['user_id'])
                )

    return redirect(url_for('index', added=1))


# ── Modifier ───────────────────────────────────────────────────────────────
@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    image_file = request.files.get('image_file')
    if image_file and image_file.filename:
        image_url = upload_image_cloudinary(image_file)
    else:
        image_url = form_str(request.form, 'image')

    genres_str = ', '.join(request.form.getlist('genres'))

    with db_cursor(commit=True) as cur:
        cur.execute('''
            UPDATE mangas
            SET nom=%s, chapitre=%s, saison=%s, fini=%s, lien=%s, note=%s, image=%s, genres=%s
            WHERE id=%s AND user_id=%s
        ''', (
            form_str(request.form, 'nom'),
            form_int(request.form, 'chapitre', default=0, min_value=0),
            form_int(request.form, 'saison', default=0, min_value=0),
            form_bool_oui_non(request.form, 'fini'),
            form_str(request.form, 'lien'),
            form_int(request.form, 'note', default=0, min_value=0, max_value=5),
            image_url,
            genres_str,
            id,
            session['user_id']
        ))

        collection_ids = {int(x) for x in request.form.getlist('collections') if x.isdigit()}
        cur.execute("DELETE FROM manga_collections WHERE manga_id = %s", (id,))
        for cid in collection_ids:
            cur.execute(
                "INSERT INTO manga_collections (manga_id, collection_id)"
                " SELECT %s, id FROM collections WHERE id = %s AND user_id = %s"
                " ON CONFLICT DO NOTHING",
                (id, cid, session['user_id'])
            )

    return redirect(url_for('index', updated=1))


@app.route('/editer/<int:id>', methods=['GET'])
def editer(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with db_cursor(dict_cursor=True) as cur:
        cur.execute('SELECT * FROM mangas WHERE id=%s AND user_id=%s', (id, session['user_id']))
        manga = cur.fetchone()
        selected_ids = set()
        if manga:
            cur.execute("SELECT collection_id FROM manga_collections WHERE manga_id = %s", (id,))
            selected_ids = {r['collection_id'] for r in cur.fetchall()}

    g = manga.get('genres') or '' if manga else ''
    manga_genres = [x.strip() for x in g.split(',') if x.strip()]
    return render_template(
        'editer.html', manga=manga, manga_genres=manga_genres,
        genres_disponibles=GENRES_DISPONIBLES,
        collections_disponibles=get_user_collections(session['user_id']),
        manga_collection_ids=selected_ids,
    )


# ── Modifier chapitre (AJAX) ─────────────────────────────────────────────────
@app.route('/modifier_chapitre/<int:id>', methods=['POST'])
def modifier_chapitre(id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    payload = request.get_json(silent=True) or {}
    try:
        changement = int(payload.get('change', 0))
    except (TypeError, ValueError):
        return jsonify({"erreur": "Requête invalide"}), 400

    with db_cursor(dict_cursor=True, commit=True) as cur:
        cur.execute("SELECT chapitre FROM mangas WHERE id=%s AND user_id=%s", (id, session['user_id']))
        manga = cur.fetchone()
        if not manga:
            return jsonify({"erreur": "Manga introuvable"}), 404
        nouveau_chapitre = max(1, int(manga['chapitre']) + changement)
        cur.execute(
            "UPDATE mangas SET chapitre=%s, derniere_lecture=%s WHERE id=%s AND user_id=%s",
            (nouveau_chapitre, datetime.now().date(), id, session['user_id'])
        )
    return jsonify({"nouveauChapitre": nouveau_chapitre})


# ── Supprimer ──────────────────────────────────────────────────────────────
@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    if 'user_id' not in session:
        return '', 403
    with db_cursor(commit=True) as cur:
        cur.execute('DELETE FROM mangas WHERE id=%s AND user_id=%s', (id, session['user_id']))
    return '', 200


# ── Lire ─────────────────────────────────────────────────────────────────────
@app.route('/lire/<int:id>')
def lire_manga(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    with db_cursor(dict_cursor=True, commit=True) as cur:
        cur.execute("SELECT lien FROM mangas WHERE id=%s AND user_id=%s", (id, session['user_id']))
        manga = cur.fetchone()
        if not manga:
            return "Manga introuvable", 404
        cur.execute("UPDATE mangas SET derniere_lecture=%s WHERE id=%s AND user_id=%s",
                    (datetime.now().date(), id, session['user_id']))
    return redirect(manga['lien'])


# ── Stats ──────────────────────────────────────────────────────────────────
@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    mangas = charger_mangas(session['user_id'])
    for m in mangas:
        m['fini'] = str(m.get('fini')).lower() == 'true'
    total = len(mangas)
    finis = sum(1 for m in mangas if m['fini'])
    en_cours = total - finis
    non_lu_count = 0
    genres_count = {}
    for m in mangas:
        for g in m.get('genres', []):
            genres_count[g] = genres_count.get(g, 0) + 1
        dl = m.get('derniere_lecture')
        if dl is None:
            continue
        try:
            d = datetime.strptime(str(dl), '%Y-%m-%d').date() if isinstance(dl, str) else dl
            if (datetime.now().date() - d).days >= 7 and not m['fini']:
                non_lu_count += 1
        except Exception:
            pass
    total_chapitres = sum(int(m.get('chapitre', 0) or 0) for m in mangas)
    if total > 0:
        moyenne = round(sum(int(m.get('note', 0)) for m in mangas) / total, 2)
        meilleur = max(mangas, key=lambda m: int(m.get('note', 0)))
        meilleur_nom = meilleur.get('nom', 'Aucun')
        meilleur_note = int(meilleur.get('note', 0))
    else:
        moyenne = 0
        meilleur_nom = "Aucun"
        meilleur_note = 0
    top_genres = sorted(genres_count.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return jsonify({
        "total": total, "finis": finis, "en_cours": en_cours,
        "non_lu_7j": non_lu_count, "total_chapitres": total_chapitres,
        "moyenne": moyenne, "meilleur_nom": meilleur_nom, "meilleur_note": meilleur_note,
        "top_genres": top_genres,
    })


# ── Exports ──────────────────────────────────────────────────────────────────
@app.route('/export')
def export_json():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    mangas = charger_mangas(session['user_id'])
    out = []
    for m in mangas:
        row = dict(m)
        if row.get('derniere_lecture') is not None:
            row['derniere_lecture'] = str(row['derniere_lecture'])
        out.append(row)
    data = json.dumps(out, ensure_ascii=False, indent=2)
    return Response(data, mimetype='application/json',
                     headers={'Content-Disposition': 'attachment; filename=mangas-sauvegarde.json'})


@app.route('/export/csv')
def export_csv():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    mangas = charger_mangas(session['user_id'])
    output = StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['id', 'nom', 'chapitre', 'saison', 'fini', 'lien', 'note', 'image', 'derniere_lecture'])
    for m in mangas:
        writer.writerow([
            m.get('id'), m.get('nom'), m.get('chapitre'), m.get('saison'),
            m.get('fini'), m.get('lien'), m.get('note'), m.get('image'),
            str(m.get('derniere_lecture') or '')
        ])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv; charset=utf-8',
                     headers={'Content-Disposition': 'attachment; filename=mangas-sauvegarde.csv'})
