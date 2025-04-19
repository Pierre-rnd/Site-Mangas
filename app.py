from flask import Flask, render_template, request, redirect, url_for , jsonify
import json

app = Flask(__name__)

def charger_mangas():
    with open('mangas.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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
    mangas = charger_mangas()
    nouveau_manga = {
        'nom': request.form['nom'],
        'chapitre': request.form['chapitre'],
        'saison': request.form['saison'],
        'fini': request.form['fini'],
        'lien': request.form['lien'],
        'note': int(request.form['note']),
        'image': request.form['image']
    }
    mangas.append(nouveau_manga)
    sauvegarder_mangas(mangas)
    return redirect(url_for('index'))

@app.route('/modifier/<int:index>', methods=['POST'])
def modifier(index):
    mangas = charger_mangas()
    mangas[index]['nom'] = request.form['nom']
    mangas[index]['chapitre'] = request.form['chapitre']
    mangas[index]['saison'] = request.form['saison']
    mangas[index]['fini'] = request.form['fini']  
    mangas[index]['lien'] = request.form['lien']
    mangas[index]['note'] = int(request.form['note'])
    mangas[index]['image'] = request.form['image']

    sauvegarder_mangas(mangas)  

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

@app.route('/supprimer/<int:index>', methods=['POST'])
def supprimer(index):
    mangas = charger_mangas()  
    try:
        del mangas[index]  
        sauvegarder_mangas(mangas)  
        return '', 200  
    except IndexError:
        return "Manga introuvable", 404


if __name__ == '__main__':
    app.run(debug=True)


