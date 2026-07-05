# -*- coding: utf-8 -*-
"""routes_rappels.py — Rappels de lecture (nouvelle fonctionnalité).

Liste les mangas non terminés que l'utilisateur n'a pas lus depuis plus de
`rappel_jours` jours (seuil personnalisable), triés du plus urgent au moins
urgent. Un badge avec le nombre de rappels est injecté automatiquement dans
tous les templates via un context_processor (voir en bas de fichier).
"""
from flask import render_template, request, redirect, url_for, jsonify, session

from core import app
from db import db_cursor
from helpers import (
    charger_mangas, enrich_mangas, get_rappel_jours, count_mangas_a_relancer,
    form_int,
)


@app.route('/rappels')
def rappels_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    seuil = get_rappel_jours(user_id)
    mangas = enrich_mangas(charger_mangas(user_id))

    a_relancer = [m for m in mangas if not m['fini'] and (
        m.get('derniere_lecture') is None or
        (m.get('jours_depuis_lecture') is not None and m['jours_depuis_lecture'] >= seuil)
    )]
    # Jamais lus d'abord (les plus "oubliés"), puis du plus ancien au plus récent
    a_relancer.sort(key=lambda m: (m.get('jours_depuis_lecture') is None,
                                    -(m.get('jours_depuis_lecture') or 10**9)))

    return render_template('rappels.html', mangas=a_relancer, seuil=seuil)


@app.route('/rappels/seuil', methods=['POST'])
def modifier_seuil_rappel():
    if 'user_id' not in session:
        return jsonify({"erreur": "Non autorisé"}), 403
    seuil = form_int(request.form, 'seuil', default=7, min_value=1, max_value=365)
    with db_cursor(commit=True) as cur:
        cur.execute("UPDATE users SET rappel_jours = %s WHERE id = %s", (seuil, session['user_id']))
    return redirect(url_for('rappels_page'))


@app.context_processor
def inject_rappels_count():
    """Rend `rappels_count` disponible dans TOUS les templates sans avoir à
    le passer explicitement dans chaque render_template()."""
    if 'user_id' in session:
        try:
            return {"rappels_count": count_mangas_a_relancer(session['user_id'])}
        except Exception:
            return {"rappels_count": 0}
    return {"rappels_count": 0}
