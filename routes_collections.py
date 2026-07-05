# -*- coding: utf-8 -*-
"""routes_collections.py — Collections personnalisées (nouvelle fonctionnalité).

Une "collection" est un dossier créé librement par l'utilisateur (ex :
"À continuer cet été", "Coup de cœur 2026", "Adaptations anime") auquel il
peut rattacher n'importe quel manga de sa bibliothèque, en plus des genres
fixes déjà existants.
"""
from flask import render_template, request, redirect, url_for, jsonify, session

from core import app
from db import db_cursor
from helpers import get_user_collections, next_collection_color, form_str


@app.route('/collections')
def collections_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    with db_cursor(dict_cursor=True) as cur:
        cur.execute("SELECT id, nom, couleur FROM collections WHERE user_id = %s ORDER BY nom", (user_id,))
        collections = cur.fetchall()
        for c in collections:
            cur.execute(
                "SELECT m.id, m.nom, m.image FROM manga_collections mc"
                " JOIN mangas m ON m.id = mc.manga_id"
                " WHERE mc.collection_id = %s ORDER BY m.nom",
                (c['id'],)
            )
            c['mangas'] = cur.fetchall()

    return render_template('collections.html', collections=collections)


@app.route('/collections/creer', methods=['POST'])
def creer_collection():
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    nom = form_str(request.form or request.get_json(silent=True) or {}, 'nom')
    if not nom:
        return jsonify({"erreur": "Le nom de la collection est requis."}), 400
    if len(nom) > 60:
        return jsonify({"erreur": "Nom trop long (60 caractères max)."}), 400

    couleur = next_collection_color(session['user_id'])
    try:
        with db_cursor(dict_cursor=True, commit=True) as cur:
            cur.execute(
                "INSERT INTO collections (user_id, nom, couleur) VALUES (%s, %s, %s) RETURNING id",
                (session['user_id'], nom, couleur)
            )
            new_id = cur.fetchone()['id']
    except Exception:
        return jsonify({"erreur": "Une collection porte déjà ce nom."}), 400

    return jsonify({"ok": True, "id": new_id, "nom": nom, "couleur": couleur})


@app.route('/collections/supprimer/<int:id>', methods=['POST'])
def supprimer_collection(id):
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM collections WHERE id=%s AND user_id=%s", (id, session['user_id']))
    return jsonify({"ok": True})
