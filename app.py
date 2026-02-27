from flask import Flask, render_template, request, redirect, url_for, jsonify, Response, session
import os, json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'une_clef_secrete')
bcrypt = Bcrypt(app)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),  
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    return conn

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                        (username, email, password_hash))
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Erreur: {e}"
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            return "Nom d'utilisateur ou mot de passe incorrect"
    return render_template('login.html')

def charger_mangas(user_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM mangas WHERE user_id = %s", (user_id,))
    mangas = cur.fetchall()
    cur.close()
    conn.close()
    return mangas

def sauvegarder_mangas(mangas):
    with open('mangas.json', 'w', encoding='utf-8') as f:
        json.dump(mangas, f, ensure_ascii=False, indent=4)

bcrypt = Bcrypt(app)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    mangas = charger_mangas(session['user_id'])

    for manga in mangas:
        manga['fini'] = str(manga['fini']).lower() == 'true'
        dl = manga.get('derniere_lecture')
        if dl:
            try:
                date_lecture = datetime.strptime(str(dl), '%Y-%m-%d').date()
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
    order = request.args.get('order', 'asc' if sort_by == 'nom' else 'desc')

    if filter_fini == 'oui':
        filter_fini_value = True
    elif filter_fini == 'non':
        filter_fini_value = False
    else:
        filter_fini_value = None

    filtered_mangas = []
    for m in mangas:
        if (search in m['nom'].lower() or search == '') and \
           (filter_fini_value is None or m['fini'] == filter_fini_value) and \
           (filter_note == '' or (filter_note and m['note'] == int(filter_note))) and \
           (not filter_non_lu or m.get('non_lu')):
            filtered_mangas.append(m)

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

    return render_template('index.html', mangas=filtered_mangas, sort=sort_by, order=order)



@app.route('/ajouter', methods=['POST'])
def ajouter():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO mangas (nom, chapitre, saison, fini, lien, note, image, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        request.form['nom'],
        request.form.get('chapitre', 0),
        request.form.get('saison', 0),
        request.form['fini'] == 'oui',
        request.form['lien'],
        int(request.form.get('note', 0)),
        request.form['image'],
        session['user_id']
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('index', added=1))


@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    conn = get_db_connection()
    cur = conn.cursor()

    nom = request.form['nom']
    chapitre = request.form.get('chapitre', 0)
    saison = request.form.get('saison', 0)
    fini = request.form['fini'] == 'oui'
    lien = request.form['lien']
    note = int(request.form.get('note', 0))
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

    cur.execute("UPDATE mangas SET chapitre = %s, derniere_lecture = %s WHERE id = %s", (nouveau_chapitre, id))
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

    return jsonify({
        "total": total,
        "finis": finis,
        "en_cours": en_cours,
        "non_lu_7j": non_lu_count,
        "total_chapitres": total_chapitres,
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


@app.route('/export/csv')
def export_csv():
    """Exporte la liste des mangas en CSV."""
    import csv
    from io import StringIO
    mangas = charger_mangas()
    output = StringIO()
    output.write('\ufeff')  # BOM UTF-8 pour Excel
    writer = csv.writer(output)
    writer.writerow(['id', 'nom', 'chapitre', 'saison', 'fini', 'lien', 'note', 'image', 'derniere_lecture'])
    for m in mangas:
        writer.writerow([
            m.get('id'), m.get('nom'), m.get('chapitre'), m.get('saison'),
            m.get('fini'), m.get('lien'), m.get('note'), m.get('image'),
            str(m.get('derniere_lecture') or '')
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=mangas-sauvegarde.csv'}
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)


