from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import psycopg2

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        port=os.environ['DB_PORT']
    )
    return conn

@app.route('/init-db')
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS mangas (
        id SERIAL PRIMARY KEY,
        nom TEXT NOT NULL,
        chapitre TEXT,
        saison TEXT,
        fini TEXT,
        lien TEXT,
        note INTEGER,
        image TEXT
    );
    ''')

    conn.commit()
    cur.close()
    conn.close()
    return "Table mangas créée avec succès !"

def charger_mangas():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM mangas ORDER BY id')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    mangas = []
    for row in rows:
        mangas.append({
            'id': row[0],
            'nom': row[1],
            'chapitre': row[2],
            'saison': row[3],
            'fini': row[4],
            'lien': row[5],
            'note': row[6],
            'image': row[7]
        })
    return mangas

@app.route('/')
def index():
    mangas = charger_mangas()

    search = request.args.get('search', '').lower()
    filter_fini = request.args.get('filter_fini', '')
    filter_note = request.args.get('filter_note', '')

    filtered_mangas = []
    for manga in mangas:
        if (search in manga['nom'].lower() or search == '') and \
           (filter_fini == '' or manga['fini'] == filter_fini) and \
           (filter_note == '' or manga['note'] == int(filter_note)):
            filtered_mangas.append(manga)

    return render_template('index.html', mangas=filtered_mangas)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO mangas (nom, chapitre, saison, fini, lien, note, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (
        request.form['nom'],
        request.form['chapitre'],
        request.form['saison'],
        request.form['fini'],
        request.form['lien'],
        int(request.form['note']),
        request.form['image']
    ))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        UPDATE mangas
        SET nom = %s, chapitre = %s, saison = %s, fini = %s, lien = %s, note = %s, image = %s
        WHERE id = %s
    ''', (
        request.form['nom'],
        request.form['chapitre'],
        request.form['saison'],
        request.form['fini'],
        request.form['lien'],
        int(request.form['note']),
        request.form['image'],
        id
    ))

    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/editer/<int:id>', methods=['GET', 'POST'])
def editer(id):
    if request.method == 'POST':
        return redirect(url_for('modifier', id=id))
    else:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM mangas WHERE id = %s', (id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            manga = {
                'id': row[0],
                'nom': row[1],
                'chapitre': row[2],
                'saison': row[3],
                'fini': row[4],
                'lien': row[5],
                'note': row[6],
                'image': row[7]
            }
            return render_template('editer.html', manga=manga, index=id)
        else:
            return "Manga introuvable", 404

@app.route('/modifier_chapitre/<int:id>', methods=['POST'])
def modifier_chapitre(id):
    changement = request.json['change']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT chapitre FROM mangas WHERE id = %s', (id,))
    row = cur.fetchone()

    if not row:
        return jsonify({"error": "Manga introuvable"}), 404

    nouveau_chapitre = str(max(1, int(row[0]) + changement))
    cur.execute('UPDATE mangas SET chapitre = %s WHERE id = %s', (nouveau_chapitre, id))

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
    cur.close()
    conn.close()
    return '', 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)
