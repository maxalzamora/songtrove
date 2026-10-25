"""SQLite storage for the songbook."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g

DEFAULT_TUNING = "E A D G B E"

SONGS_TABLE = f"""
CREATE TABLE IF NOT EXISTS songs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    artist     TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    tuning     TEXT    NOT NULL DEFAULT '{DEFAULT_TUNING}',
    capo       INTEGER NOT NULL DEFAULT 0,
    rating     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
"""

TARGET_COLUMNS = frozenset(
    {
        "id",
        "title",
        "artist",
        "content",
        "tuning",
        "capo",
        "rating",
        "created_at",
        "updated_at",
    }
)

INDEX = """
CREATE INDEX IF NOT EXISTS idx_songs_created ON songs (created_at DESC);
"""

SCHEMA = SONGS_TABLE + INDEX

SORT_ORDERS = {
    "recent": "created_at DESC, id DESC",
    "title": "title COLLATE NOCASE ASC, artist COLLATE NOCASE ASC",
    "artist": "artist COLLATE NOCASE ASC, title COLLATE NOCASE ASC",
    "rating": "rating DESC, title COLLATE NOCASE ASC",
}


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        database = get_db()
        _migrate_schema(database)
        database.executescript(SCHEMA)
        database.execute(
            "UPDATE songs SET tuning = ? WHERE TRIM(COALESCE(tuning, '')) = ''",
            (DEFAULT_TUNING,),
        )
        database.commit()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = Path(current_app.config["DATABASE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error=None) -> None:
    database = g.pop("db", None)
    if database is not None:
        database.close()


def list_songs(query: str = "", sort: str = "recent") -> list[sqlite3.Row]:
    order = SORT_ORDERS.get(sort, SORT_ORDERS["recent"])
    database = get_db()
    query = (query or "").strip()
    if query:
        like = f"%{query}%"
        rows = database.execute(
            f"""SELECT * FROM songs
                WHERE title LIKE ? OR artist LIKE ?
                ORDER BY {order}""",
            (like, like),
        )
    else:
        rows = database.execute(f"SELECT * FROM songs ORDER BY {order}")
    return rows.fetchall()


def count_songs() -> int:
    row = get_db().execute("SELECT COUNT(*) AS total FROM songs").fetchone()
    return int(row["total"]) if row else 0


def get_song(song_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()


def add_manual_song(
    *,
    title: str,
    artist: str,
    content: str,
    tuning: str = DEFAULT_TUNING,
    capo: int = 0,
    rating: int = 0,
) -> int:
    """Store a song entered by hand and return its new id."""
    now = _now()
    database = get_db()
    cursor = database.execute(
        """INSERT INTO songs
               (title, artist, content, tuning, capo, rating,
                created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, artist, content, tuning, capo, rating, now, now),
    )
    database.commit()
    return int(cursor.lastrowid)


def update_settings(
    song_id: int, *, capo: int | None = None, rating: int | None = None
) -> None:
    assignments = []
    parameters: list[int | str] = []
    if capo is not None:
        assignments.append("capo = ?")
        parameters.append(capo)
    if rating is not None:
        assignments.append("rating = ?")
        parameters.append(rating)
    if not assignments:
        return

    assignments.append("updated_at = ?")
    parameters.extend([_now(), song_id])
    database = get_db()
    database.execute(
        f"UPDATE songs SET {', '.join(assignments)} WHERE id = ?", parameters
    )
    database.commit()


def update_song(
    song_id: int,
    *,
    title: str,
    artist: str,
    content: str,
    tuning: str,
    capo: int,
    rating: int,
) -> None:
    """Replace every editable field on a song."""
    database = get_db()
    database.execute(
        """UPDATE songs
              SET title = ?, artist = ?, content = ?, tuning = ?,
                  capo = ?, rating = ?, updated_at = ?
            WHERE id = ?""",
        (title, artist, content, tuning, capo, rating, _now(), song_id),
    )
    database.commit()


def delete_song(song_id: int) -> None:
    database = get_db()
    database.execute("DELETE FROM songs WHERE id = ?", (song_id,))
    database.commit()


def _migrate_schema(database: sqlite3.Connection) -> None:
    """Rebuild older song tables, keeping every row and its metadata."""
    columns = {
        row["name"] for row in database.execute("PRAGMA table_info(songs)").fetchall()
    }
    if not columns or columns == TARGET_COLUMNS:
        return

    database.execute("BEGIN IMMEDIATE")
    try:
        database.execute("ALTER TABLE songs RENAME TO songs_legacy")
        database.execute("DROP INDEX IF EXISTS idx_songs_created")
        database.execute(SONGS_TABLE)
        database.execute(
            """INSERT INTO songs
                   (id, title, artist, content, tuning, capo, rating,
                    created_at, updated_at)
               SELECT id, title, artist, content,
                      CASE
                          WHEN TRIM(COALESCE(tuning, '')) = '' THEN ?
                          ELSE tuning
                      END,
                      capo, rating, created_at, updated_at
                 FROM songs_legacy""",
            (DEFAULT_TUNING,),
        )
        database.execute("DROP TABLE songs_legacy")
    except Exception:
        database.rollback()
        raise
    else:
        database.commit()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
