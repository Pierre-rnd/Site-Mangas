# Site Manga - Projet Personnel

> Ce projet est un site web de gestion de mangas développé à des fins **personnelles et pédagogiques**.  
> Il n'est pas destiné à un usage commercial.

---

## 🚀 À propos

Ce site permet de **gérer une collection de mangas** avec une interface simple et intuitive.  
Il a été développé dans le cadre de mes projets personnels et pour améliorer mes compétences en développement web et Python.

---

## 🛠 Fonctionnalités

- Ajouter, modifier et supprimer des mangas (CRUD complet)
- Filtrer et rechercher des mangas dans la collection (nom, genre, note, statut, collection)
- **Collections personnalisées** : crée tes propres dossiers (ex: "Coup de cœur 2026") et rattache-y des mangas, en plus des genres fixes
- **Rappels de lecture** : une page dédiée liste les mangas non lus depuis un certain nombre de jours (seuil personnalisable), avec un badge de notification dans le menu
- Pagination (12 mangas par page) sur la liste principale et la galerie communautaire
- Galerie communautaire : voir les mangas des autres utilisateurs, les copier, commentaires, top 3
- Stockage via PostgreSQL, images hébergées sur Cloudinary
- Interface responsive et moderne (thème clair / sombre)
- Export JSON / CSV

---

## 🖥 Technologies utilisées

- **Langage :** Python
- **Framework :** Flask
- **Front-end :** HTML, CSS, JavaScript
- **Stockage :** PostgreSQL (+ Cloudinary pour les images)

---

## 🗂 Architecture du code

Le backend est découpé en modules pour rester lisible et facile à faire évoluer :

| Fichier                  | Rôle                                                              |
|--------------------------|--------------------------------------------------------------------|
| `core.py`                | Instance Flask, configuration, constantes (genres, pagination...) |
| `db.py`                  | Connexion PostgreSQL + création/migration du schéma (une seule fois au démarrage) |
| `helpers.py`             | Fonctions partagées : validation de formulaires, enrichissement des données |
| `routes_auth.py`         | Inscription / connexion / déconnexion |
| `routes_mangas.py`       | CRUD des mangas, pagination, statistiques, exports |
| `routes_community.py`    | Galerie publique, top 3, commentaires, copie de fiches |
| `routes_collections.py`  | Collections personnalisées |
| `routes_rappels.py`      | Rappels de lecture |
| `app.py`                 | Point d'entrée : assemble tous les modules et lance le serveur |

Toutes les routes gardent les mêmes noms et URLs qu'avant (`/`, `/login`, `/galerie`, ...), donc aucune modification n'est nécessaire côté déploiement (Render, variables d'environnement, etc.).

### Variables d'environnement nécessaires
`SECRET_KEY`, `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.

Les tables `users` et `mangas` doivent déjà exister en base (colonnes de base : id, username, email, password_hash pour `users` ; id, nom, chapitre, saison, fini, lien, note, image, user_id, derniere_lecture pour `mangas`). Toutes les autres tables/colonnes (genres, collections, rappel_jours, top3, commentaires) sont créées automatiquement au démarrage.

---

## ⚠️ Usage

Ce site est **strictement personnel**.

