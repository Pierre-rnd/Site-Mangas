from flask import Flask, render_template, request, redirect, url_for , jsonify
import os
import json
import psycopg2

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
    cur = conn.cursor()
    cur.execute('SELECT * FROM mangas')
    mangas = cur.fetchall()
    conn.close()
    return mangas

def sauvegarder_mangas(mangas):
    with open('mangas.json', 'w', encoding='utf-8') as f:
        json.dump(mangas, f, ensure_ascii=False, indent=4)

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

    return redirect(url_for('index'))


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

    return redirect(url_for('index'))



@app.route('/editer/<int:index>', methods=['GET', 'POST'])
def editer(index):
    mangas = charger_mangas()
    if request.method == 'POST':
        mangas[index] = {
            'nom': request.form['nom'],
            'chapitre': request.form['chapitre'],
            'saison': request.form['saison'],
            'fini': request.form['fini'],
            'lien': request.form['lien'],
            'note': int(request.form['note']),
            'image': request.form['image']
        }
        with open('mangas.json', 'w') as f:
            json.dump(mangas, f)
        return redirect(url_for('index'))
    else:
        manga = mangas[index]
        return render_template('editer.html', manga=manga, index=index)




@app.route('/modifier_chapitre/<int:index>', methods=['POST'])
def modifier_chapitre(index):
    mangas = charger_mangas()
    changement = request.json['change']

    manga = mangas[index]
    manga['chapitre'] = str(max(1, int(manga['chapitre']) + changement))

    sauvegarder_mangas(mangas)

    return jsonify({"nouveauChapitre": manga['chapitre']})

@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('DELETE FROM mangas WHERE id = %s', (id,))
    conn.commit()
    conn.close()

    return '', 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)


