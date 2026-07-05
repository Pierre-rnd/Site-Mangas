# -*- coding: utf-8 -*-
"""routes_auth.py — Inscription, connexion, déconnexion."""
import re

from flask import render_template, request, redirect, url_for, session

from core import app, bcrypt
from db import db_cursor

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # ── Validation côté serveur (avant, aucune validation n'était faite) ──
        if len(username) < 3:
            return render_template('register.html', error="Le nom d'utilisateur doit faire au moins 3 caractères.",
                                    username=username, email=email)
        if not EMAIL_RE.match(email):
            return render_template('register.html', error="Adresse email invalide.",
                                    username=username, email=email)
        if len(password) < 6:
            return render_template('register.html', error="Le mot de passe doit faire au moins 6 caractères.",
                                    username=username, email=email)

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash)
                )
        except Exception as e:
            err = str(e).lower()
            if 'email' in err:
                error = "Cette adresse email est déjà utilisée."
            elif 'username' in err:
                error = "Ce nom d'utilisateur est déjà pris."
            else:
                error = "Une erreur est survenue, veuillez réessayer."
            return render_template('register.html', error=error, username=username, email=email)

        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        with db_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error="Nom d'utilisateur ou mot de passe incorrect")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
