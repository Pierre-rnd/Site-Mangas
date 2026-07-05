# -*- coding: utf-8 -*-
"""routes_community.py — Galerie publique, top 3, commentaires, copie de fiches."""
from datetime import datetime

from flask import render_template, request, redirect, url_for, jsonify, session

from core import app, PER_PAGE
from db import db_cursor
from helpers import form_int, paginate


@app.route('/galerie')
def galerie():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').lower()
    filter_note = request.args.get('filter_note', '')
    filter_fini = request.args.get('filter_fini', '')
    page = form_int(request.args, 'page', default=1, min_value=1)

    with db_cursor(dict_cursor=True) as cur:
        cur.execute(
            "SELECT m.*, u.username AS owner FROM mangas m"
            " JOIN users u ON m.user_id = u.id"
            " WHERE m.user_id != %s ORDER BY m.nom",
            (session['user_id'],)
        )
        all_mangas = cur.fetchall()

        cur.execute("SELECT nom FROM mangas WHERE user_id = %s", (session['user_id'],))
        my_noms = {row['nom'].lower() for row in cur.fetchall()}

        for m in all_mangas:
            m['fini'] = str(m.get('fini')).lower() == 'true'
            m['already_have'] = m['nom'].lower() in my_noms

        if search:
            all_mangas = [m for m in all_mangas if search in m['nom'].lower()]
        if filter_note:
            all_mangas = [m for m in all_mangas if m['note'] == int(filter_note)]
        if filter_fini == 'oui':
            all_mangas = [m for m in all_mangas if m['fini']]
        elif filter_fini == 'non':
            all_mangas = [m for m in all_mangas if not m['fini']]

        total_resultats = len(all_mangas)
        all_mangas, total_pages, page = paginate(all_mangas, page, PER_PAGE)

        if request.args.get('ajax') == '1':
            return render_template('_galerie_cards.html', mangas=all_mangas,
                                    page=page, total_pages=total_pages, total_resultats=total_resultats)

        # Top 3 de tous les utilisateurs
        cur.execute(
            "SELECT t.rank, t.user_id, u.username,"
            " m.id AS manga_id, m.nom, m.image, m.note, m.genres, m.fini"
            " FROM top3 t"
            " JOIN users u ON t.user_id = u.id"
            " JOIN mangas m ON t.manga_id = m.id"
            " ORDER BY u.username, t.rank"
        )
        top3_rows = cur.fetchall()
        top3_by_user = {}
        for row in top3_rows:
            uid = row['user_id']
            if uid not in top3_by_user:
                top3_by_user[uid] = {'username': row['username'], 'mangas': []}
            d = dict(row)
            d['fini'] = str(d.get('fini')).lower() == 'true'
            top3_by_user[uid]['mangas'].append(d)
        top3_users = list(top3_by_user.values())

        # Mangas + top3 de l'utilisateur courant (pour le sélecteur modal)
        cur.execute("SELECT id, nom, note FROM mangas WHERE user_id = %s ORDER BY nom", (session['user_id'],))
        my_mangas = cur.fetchall()

        cur.execute(
            "SELECT t.rank, m.id, m.nom FROM top3 t"
            " JOIN mangas m ON t.manga_id = m.id"
            " WHERE t.user_id = %s ORDER BY t.rank",
            (session['user_id'],)
        )
        my_top3 = {row['rank']: row for row in cur.fetchall()}

    return render_template('galerie.html',
                            mangas=all_mangas,
                            top3_users=top3_users,
                            my_mangas=my_mangas,
                            my_top3=my_top3,
                            current_user_id=session['user_id'],
                            page=page, total_pages=total_pages, total_resultats=total_resultats)


@app.route('/top3', methods=['POST'])
def save_top3():
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    data = request.get_json(force=True, silent=True) or {}
    try:
        ids = [int(x) for x in data.get('ids', []) if x]
    except (TypeError, ValueError):
        return jsonify({"erreur": "Requête invalide"}), 400
    if len(ids) != len(set(ids)):
        return jsonify({"erreur": "Doublons non autorisés"}), 400
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM top3 WHERE user_id = %s", (session['user_id'],))
        for rank, manga_id in enumerate(ids[:3], start=1):
            cur.execute("INSERT INTO top3 (user_id, manga_id, rank) VALUES (%s, %s, %s)",
                        (session['user_id'], manga_id, rank))
    return jsonify({"ok": True})


@app.route('/commentaires/<int:manga_id>', methods=['GET'])
def get_commentaires(manga_id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    with db_cursor(dict_cursor=True) as cur:
        cur.execute(
            "SELECT c.id, c.texte, c.created_at, u.username, c.user_id"
            " FROM commentaires c JOIN users u ON c.user_id = u.id"
            " WHERE c.manga_id = %s ORDER BY c.created_at DESC",
            (manga_id,)
        )
        rows = cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['created_at'] = str(d['created_at'])[:10] if d.get('created_at') else ''
        d['is_mine'] = (d['user_id'] == session['user_id'])
        result.append(d)
    return jsonify(result)


@app.route('/commentaires/<int:manga_id>', methods=['POST'])
def post_commentaire(manga_id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    texte = ((request.get_json(force=True, silent=True) or {}).get('texte') or '').strip()
    if not texte or len(texte) > 1000:
        return jsonify({"erreur": "Texte invalide"}), 400
    with db_cursor(dict_cursor=True, commit=True) as cur:
        cur.execute("SELECT id FROM mangas WHERE id=%s AND user_id=%s", (manga_id, session['user_id']))
        if not cur.fetchone():
            return jsonify({"erreur": "Non autorisé"}), 403
        cur.execute(
            "INSERT INTO commentaires (manga_id, user_id, texte, created_at)"
            " VALUES (%s,%s,%s,%s) RETURNING id, created_at",
            (manga_id, session['user_id'], texte, datetime.now().date())
        )
        row = cur.fetchone()
    return jsonify({"ok": True, "id": row['id'], "created_at": str(row['created_at'])[:10]})


@app.route('/commentaires/delete/<int:comment_id>', methods=['POST'])
def delete_commentaire(comment_id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM commentaires WHERE id=%s AND user_id=%s", (comment_id, session['user_id']))
    return jsonify({"ok": True})


@app.route('/copier/<int:id>', methods=['POST'])
def copier_manga(id):
    """Copie la fiche d'un manga d'un autre utilisateur dans sa propre collection."""
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403

    with db_cursor(dict_cursor=True, commit=True) as cur:
        cur.execute("SELECT * FROM mangas WHERE id=%s AND user_id != %s", (id, session['user_id']))
        source = cur.fetchone()
        if not source:
            return jsonify({"erreur": "Manga introuvable"}), 404

        cur.execute('''
            INSERT INTO mangas (nom, chapitre, saison, fini, lien, note, image, user_id, genres)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            source['nom'],
            1,  # chapitre remis à 1
            source['saison'],
            source['fini'],
            source['lien'],
            source['note'],
            source['image'],
            session['user_id'],
            source.get('genres', '')
        ))

    return jsonify({"ok": True, "nom": source['nom']})
