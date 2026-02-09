from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta


def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'dpg-d020pojuibrs73b8savg-a'),  
        database=os.getenv('DB_NAME', 'mangas_0ps5'),
        user=os.getenv('DB_USER', 'mangas_0ps5_user'),
        password=os.getenv('DB_PASSWORD', 'jV4ofeNqdzvQX1HroOxjaevprGyO5y77')
    )
    return conn

app = Flask(__name__)


def charger_mangas():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM mangas")
    mangas = cur.fetchall()

    cur.close()
    conn.close()

    return mangas

def sauvegarder_mangas(mangas):
    with open('mangas.json', 'w', encoding='utf-8') as f:
        json.dump(mangas, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    mangas = charger_mangas()
    
    for manga in mangas:
        manga['fini'] = str(manga['fini']).lower() == 'true'

        derniere_lecture = manga.get('derniere_lecture')

        if derniere_lecture:
            try:
                date_lecture = datetime.strptime(str(derniere_lecture), '%Y-%m-%d').date()
                delta = datetime.now().date() - date_lecture
                manga['non_lu'] = (delta.days >= 7 and not manga['fini'])
                if delta.days == 0:
                    manga['last_read_label'] = "Lu aujourd'hui"
                elif delta.days == 1:
                    manga['last_read_label'] = "Lu hier"
                else:
                    manga['last_read_label'] = f"Lu il y a {delta.days} jours"
            except Exception:
                manga['non_lu'] = False
                manga['last_read_label'] = "—"
        else:
            manga['non_lu'] = False
            manga['last_read_label'] = "Jamais lu"  

    search = request.args.get('search', '').lower()
    filter_fini = request.args.get('filter_fini', '')
    filter_note = request.args.get('filter_note', '')
    filter_non_lu = request.args.get('non_lu', '') == '1'
    sort_by = request.args.get('sort', 'nom')

    if filter_fini == 'oui':
        filter_fini_value = True
    elif filter_fini == 'non':
        filter_fini_value = False
    else:
        filter_fini_value = None

    filtered_mangas = []
    for manga in mangas:
        if (search in manga['nom'].lower() or search == '') and \
           (filter_fini_value is None or manga['fini'] == filter_fini_value) and \
           (filter_note == '' or (filter_note and manga['note'] == int(filter_note))) and \
           (not filter_non_lu or manga.get('non_lu')):
            filtered_mangas.append(manga)

    # Tri
    if sort_by == 'note':
        filtered_mangas.sort(key=lambda m: int(m.get('note', 0)), reverse=True)
    elif sort_by == 'derniere_lecture':
        def _date_key(m):
            d = m.get('derniere_lecture')
            if d is None:
                return datetime.min.date()
            try:
                return datetime.strptime(str(d), '%Y-%m-%d').date() if isinstance(d, str) else d
            except Exception:
                return datetime.min.date()
        filtered_mangas.sort(key=_date_key, reverse=True)
    elif sort_by == 'chapitre':
        filtered_mangas.sort(key=lambda m: int(m.get('chapitre', 0) or 0), reverse=True)
    else:
        filtered_mangas.sort(key=lambda m: m['nom'].lower())

    return render_template('index.html', mangas=filtered_mangas, sort=sort_by)



@app.route('/ajouter', methods=['POST'])
def ajouter():
    conn = get_db_connection()
    cur = conn.cursor()

    nom = request.form['nom']
    chapitre = request.form['chapitre']
    saison = request.form['saison']
    fini = request.form['fini'] == 'oui'
    lien = request.form['lien']
    note = int(request.form['note'])
    image = request.form['image']

    cur.execute('''
        INSERT INTO mangas (nom, chapitre, saison, fini, lien, note, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (nom, chapitre, saison, fini, lien, note, image))

    conn.commit()
    conn.close()

    return redirect(url_for('index', added=1))


@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    conn = get_db_connection()
    cur = conn.cursor()

    nom = request.form['nom']
    chapitre = request.form['chapitre']
    saison = request.form['saison']
    fini = request.form['fini'] == 'oui'
    lien = request.form['lien']
    note = int(request.form['note'])
    image = request.form['image']

    cur.execute('''
        UPDATE mangas
        SET nom = %s, chapitre = %s, saison = %s, fini = %s, lien = %s, note = %s, image = %s
        WHERE id = %s
    ''', (nom, chapitre, saison, fini, lien, note, image, id))

    conn.commit()
    conn.close()

    return redirect(url_for('index', updated=1))


@app.route('/editer/<int:id>', methods=['GET'])
def editer(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute('SELECT * FROM mangas WHERE id = %s', (id,))
    manga = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('editer.html', manga=manga)




@app.route('/modifier_chapitre/<int:id>', methods=['POST'])
def modifier_chapitre(id):
    changement = request.json['change']

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT chapitre FROM mangas WHERE id = %s", (id,))
    manga = cur.fetchone()

    if not manga:
        return jsonify({"erreur": "Manga introuvable"}), 404

    nouveau_chapitre = max(1, int(manga['chapitre']) + changement)

    cur.execute("UPDATE mangas SET chapitre = %s WHERE id = %s", (nouveau_chapitre, id))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"nouveauChapitre": nouveau_chapitre})

@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('DELETE FROM mangas WHERE id = %s', (id,))
    conn.commit()
    conn.close()

    return '', 200

@app.route('/stats')
def stats():
    mangas = charger_mangas()

    for m in mangas:
        m['fini'] = str(m.get('fini')).lower() == 'true'

    total = len(mangas)
    finis = sum(1 for m in mangas if m['fini'])
    en_cours = total - finis
    non_lu_count = 0
    for m in mangas:
        dl = m.get('derniere_lecture')
        if dl is None:
            continue
        try:
            d = datetime.strptime(str(dl), '%Y-%m-%d').date() if isinstance(dl, str) else dl
            if (datetime.now().date() - d).days >= 7 and not m['fini']:
                non_lu_count += 1
        except Exception:
            pass

    if total > 0:
        moyenne = round(sum(int(m.get('note', 0)) for m in mangas) / total, 2)
        meilleur = max(mangas, key=lambda m: int(m.get('note', 0)))
        meilleur_nom = meilleur.get('nom', 'Aucun')
        meilleur_note = int(meilleur.get('note', 0))
    else:
        moyenne = 0
        meilleur_nom = "Aucun"
        meilleur_note = 0

    return jsonify({
        "total": total,
        "finis": finis,
        "en_cours": en_cours,
        "non_lu_7j": non_lu_count,
        "moyenne": moyenne,
        "meilleur_nom": meilleur_nom,
        "meilleur_note": meilleur_note
    })


@app.route('/lire/<int:id>')
def lire_manga(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT lien FROM mangas WHERE id = %s", (id,))
    manga = cur.fetchone()

    if not manga:
        cur.close()
        conn.close()
        return "Manga introuvable", 404

    cur.execute("UPDATE mangas SET derniere_lecture = %s WHERE id = %s", (datetime.now().date(), id))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(manga['lien'])


@app.route('/export')
def export_json():
    """Exporte la liste complète des mangas en JSON (sauvegarde)."""
    mangas = charger_mangas()
    out = []
    for m in mangas:
        row = dict(m)
        if row.get('derniere_lecture') is not None:
            row['derniere_lecture'] = str(row['derniere_lecture'])
        out.append(row)
    data = json.dumps(out, ensure_ascii=False, indent=2)
    return Response(
        data,
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=mangas-sauvegarde.json'}
    )


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)


