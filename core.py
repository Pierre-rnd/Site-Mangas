# -*- coding: utf-8 -*-
"""
core.py — Instanciation centrale de l'application Flask et de ses extensions.

Tous les autres modules de routes importent `app`, `bcrypt` depuis ce fichier
pour partager la même instance Flask, sans passer par des Blueprints.
Cela permet de garder les mêmes noms d'endpoints (index, login, galerie, ...)
que dans l'ancien app.py monolithique, donc tous les `url_for(...)` existants
dans les templates continuent de fonctionner sans modification.
"""
import os
from flask import Flask
from flask_bcrypt import Bcrypt
import cloudinary

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'une_clef_secrete')

# Cookies de session un peu plus stricts par défaut (voir README > Sécurité)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 Mo max par upload

bcrypt = Bcrypt(app)

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

# Nombre de mangas affichés par page (index et galerie)
PER_PAGE = 12

# Seuil par défaut (en jours) avant qu'un manga soit considéré "à relancer"
DEFAULT_RAPPEL_JOURS = 7

GENRES_DISPONIBLES = [
    "Action", "Aventure", "Comédie", "Drame", "Fantasy",
    "Horreur", "Isekai", "Josei", "Mahou Shoujo", "Mecha",
    "Mystère", "Romance", "Sci-Fi", "Seinen", "Shojo",
    "Shonen", "Slice of Life", "Sports", "Surnaturel", "Thriller",
    "Manwha", "Manhua", "Webtoon", "Yaoi", "Yuri"
]

# Palette de couleurs assignées automatiquement aux collections (cyclique)
COLLECTION_COLORS = [
    "#7c5cff", "#ff6b81", "#2ec4b6", "#ff9f1c", "#4c9bf5",
    "#e84393", "#00b894", "#fdcb6e", "#6c5ce7", "#0984e3",
]
