-- Migration : tables top3 et commentaires
-- À exécuter UNE FOIS sur la base de données

CREATE TABLE IF NOT EXISTS top3 (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    manga_id  INTEGER NOT NULL REFERENCES mangas(id) ON DELETE CASCADE,
    rank      SMALLINT NOT NULL CHECK (rank BETWEEN 1 AND 3),
    PRIMARY KEY (user_id, rank)
);

CREATE TABLE IF NOT EXISTS commentaires (
    id         SERIAL PRIMARY KEY,
    manga_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    texte      TEXT NOT NULL,
    created_at DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_commentaires_manga ON commentaires(manga_id);
