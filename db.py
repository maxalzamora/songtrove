"""SQLite storage for Songtrove."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, g

DEFAULT_TUNING = "E A D G B E"

ROLE_ADMIN = "admin"
ROLE_MEMBER = "member"
ROLES = (ROLE_ADMIN, ROLE_MEMBER)

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT    NOT NULL COLLATE NOCASE UNIQUE,
    password_hash       TEXT    NOT NULL,
    role                TEXT    NOT NULL DEFAULT 'member'
                                CHECK (role IN ('admin', 'member')),
    is_active           INTEGER NOT NULL DEFAULT 1,
    is_guest            INTEGER NOT NULL DEFAULT 0,
    session_version     INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL,
    last_login_at       TEXT    NOT NULL DEFAULT '',
    password_changed_at TEXT    NOT NULL DEFAULT ''
);
"""

SONGS_TABLE = f"""
CREATE TABLE IF NOT EXISTS songs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   INTEGER NOT NULL DEFAULT 0,
    title      TEXT    NOT NULL,
    artist     TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    notes      TEXT    NOT NULL DEFAULT '',
    source_url TEXT    NOT NULL DEFAULT '',
    tags       TEXT    NOT NULL DEFAULT '',
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
        "owner_id",
        "title",
        "artist",
        "content",
        "notes",
        "source_url",
        "tags",
        "tuning",
        "capo",
        "rating",
        "created_at",
        "updated_at",
    }
)

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_songs_created ON songs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_songs_owner_created
    ON songs (owner_id, created_at DESC);
"""

SCHEMA = USERS_TABLE + SONGS_TABLE + INDEXES


class UsernameTaken(ValueError):
    """Raised when a username already exists, ignoring case."""


SORT_ORDERS = {
    "recent": "created_at DESC, id DESC",
    "title": "title COLLATE NOCASE ASC, artist COLLATE NOCASE ASC",
    "artist": "artist COLLATE NOCASE ASC, title COLLATE NOCASE ASC",
    "rating": "rating DESC, title COLLATE NOCASE ASC",
}

TAG_SPLIT = re.compile(r"[,\s]+")


def parse_tags(value) -> list[str]:
    """Return clean, lower-case tags from text or a list of tags."""
    if isinstance(value, (list, tuple, set)):
        raw = " ".join(str(item) for item in value)
    else:
        raw = str(value or "")

    tags = []
    seen = set()
    for token in TAG_SPLIT.split(raw):
        tag = token.strip().lstrip("#").casefold()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def normalize_tags(value) -> str:
    """Store tags in one canonical, comma-separated form."""
    return ",".join(parse_tags(value))


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        database = get_db()
        _migrate_schema(database)
        database.executescript(SCHEMA)
        _migrate_users_schema(database)
        database.execute(
            "UPDATE songs SET tuning = ? WHERE TRIM(COALESCE(tuning, '')) = ''",
            (DEFAULT_TUNING,),
        )
        database.commit()
        _ensure_bootstrap_admin(database, app.config)
        _assign_orphan_songs(database)
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


def list_songs(
    user_id: int,
    query: str = "",
    sort: str = "recent",
    *,
    tag: str = "",
    rating: str = "",
    tuning: str = "",
) -> list[sqlite3.Row]:
    order = SORT_ORDERS.get(sort, SORT_ORDERS["recent"])
    database = get_db()
    query = str(query or "").strip()
    clauses = ["owner_id = ?"]
    parameters: list[str | int] = [user_id]

    if query:
        search_query = (
            query[1:] if query.startswith("#") and len(query) > 1 else query
        )
        like = f"%{search_query}%"
        clauses.append(
            "(title LIKE ? OR artist LIKE ? OR notes LIKE ? OR tags LIKE ?)"
        )
        parameters.extend([like, like, like, like])

    tag = str(tag or "").strip().lstrip("#").casefold()
    if tag:
        clauses.append("instr(',' || tags || ',', ?) > 0")
        parameters.append(f",{tag},")

    rating = str(rating or "").strip()
    if rating == "0":
        clauses.append("rating = 0")
    elif rating in {"3", "4", "5"}:
        clauses.append("rating >= ?")
        parameters.append(int(rating))

    tuning = str(tuning or "").strip()
    if tuning:
        clauses.append("tuning = ?")
        parameters.append(tuning)

    where = f"WHERE {' AND '.join(clauses)}"
    rows = database.execute(
        f"SELECT * FROM songs {where} ORDER BY {order}", parameters
    )
    return rows.fetchall()


def list_tags(user_id: int) -> list[str]:
    tags = set()
    for row in get_db().execute(
        "SELECT tags FROM songs WHERE owner_id = ? AND TRIM(tags) <> ''",
        (user_id,),
    ).fetchall():
        tags.update(parse_tags(row["tags"]))
    return sorted(tags)


def list_tunings(user_id: int) -> list[str]:
    rows = get_db().execute(
        """SELECT DISTINCT tuning FROM songs
            WHERE owner_id = ? AND TRIM(COALESCE(tuning, '')) <> ''
            ORDER BY tuning COLLATE NOCASE ASC""",
        (user_id,),
    ).fetchall()
    return [row["tuning"] for row in rows]


def count_songs(user_id: int) -> int:
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM songs WHERE owner_id = ?", (user_id,)
    ).fetchone()
    return int(row["total"]) if row else 0


def get_song(song_id: int, user_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM songs WHERE id = ? AND owner_id = ?",
        (song_id, user_id),
    ).fetchone()


def add_manual_song(
    *,
    user_id: int,
    title: str,
    artist: str,
    content: str,
    notes: str = "",
    source_url: str = "",
    tags: str = "",
    tuning: str = DEFAULT_TUNING,
    capo: int = 0,
    rating: int = 0,
) -> int:
    """Store a song entered by hand and return its new id."""
    now = _now()
    database = get_db()
    cursor = database.execute(
        """INSERT INTO songs
               (owner_id, title, artist, content, notes, source_url, tags,
                tuning, capo, rating, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            title,
            artist,
            content,
            notes,
            source_url,
            normalize_tags(tags),
            tuning,
            capo,
            rating,
            now,
            now,
        ),
    )
    database.commit()
    return int(cursor.lastrowid)


def update_settings(
    song_id: int,
    *,
    user_id: int,
    capo: int | None = None,
    rating: int | None = None,
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
    parameters.extend([_now(), song_id, user_id])
    database = get_db()
    database.execute(
        f"""UPDATE songs SET {', '.join(assignments)}
             WHERE id = ? AND owner_id = ?""",
        parameters,
    )
    database.commit()


def update_song(
    song_id: int,
    *,
    user_id: int,
    title: str,
    artist: str,
    content: str,
    notes: str = "",
    source_url: str = "",
    tags: str = "",
    tuning: str,
    capo: int,
    rating: int,
) -> None:
    """Replace every editable field on a song."""
    database = get_db()
    database.execute(
        """UPDATE songs
              SET title = ?, artist = ?, content = ?, notes = ?,
                  source_url = ?, tags = ?, tuning = ?, capo = ?,
                  rating = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?""",
        (
            title,
            artist,
            content,
            notes,
            source_url,
            normalize_tags(tags),
            tuning,
            capo,
            rating,
            _now(),
            song_id,
            user_id,
        ),
    )
    database.commit()


def delete_song(song_id: int, *, user_id: int) -> None:
    database = get_db()
    database.execute(
        "DELETE FROM songs WHERE id = ? AND owner_id = ?", (song_id, user_id)
    )
    database.commit()


def list_users() -> list[sqlite3.Row]:
    return get_db().execute(
        """SELECT id, username, role, is_active, created_at, last_login_at,
                  password_changed_at
             FROM users
            ORDER BY username COLLATE NOCASE ASC"""
    ).fetchall()


def get_user(user_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
        (username,),
    ).fetchone()


def count_users() -> int:
    row = get_db().execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"]) if row else 0


def count_active_admins() -> int:
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM users WHERE role = ? AND is_active = 1",
        (ROLE_ADMIN,),
    ).fetchone()
    return int(row["total"]) if row else 0


def create_user(
    *,
    username: str,
    password_hash: str,
    role: str = ROLE_MEMBER,
    is_active: bool = True,
    is_guest: bool = False,
) -> int:
    if role not in ROLES:
        raise ValueError("Unknown role.")
    now = _now()
    database = get_db()
    try:
        cursor = database.execute(
            """INSERT INTO users
                   (username, password_hash, role, is_active, is_guest,
                    created_at, last_login_at, password_changed_at)
               VALUES (?, ?, ?, ?, ?, ?, '', ?)""",
            (
                username,
                password_hash,
                role,
                1 if is_active else 0,
                1 if is_guest else 0,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as error:
        raise UsernameTaken(username) from error
    database.commit()
    return int(cursor.lastrowid)


def set_user_active(user_id: int, is_active: bool) -> None:
    database = get_db()
    database.execute(
        "UPDATE users SET is_active = ?, "
        "session_version = session_version + 1 WHERE id = ?",
        (1 if is_active else 0, user_id),
    )
    database.commit()


def set_user_role(user_id: int, role: str) -> None:
    if role not in ROLES:
        raise ValueError("Unknown role.")
    database = get_db()
    database.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    database.commit()


def set_user_password(user_id: int, password_hash: str) -> None:
    database = get_db()
    database.execute(
        "UPDATE users SET password_hash = ?, password_changed_at = ?, "
        "session_version = session_version + 1 WHERE id = ?",
        (password_hash, _now(), user_id),
    )
    database.commit()


def record_login(user_id: int) -> None:
    database = get_db()
    database.execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?", (_now(), user_id)
    )
    database.commit()


def _ensure_bootstrap_admin(database: sqlite3.Connection, config) -> None:
    """Create the first admin from the environment when the registry is empty."""
    total = database.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    if total and int(total["total"]) > 0:
        return

    username = str(config.get("BOOTSTRAP_ADMIN_USERNAME") or "").strip()
    password_hash = str(config.get("BOOTSTRAP_ADMIN_PASSWORD_HASH") or "").strip()
    if not username or not password_hash:
        raise RuntimeError(
            "No users exist. Set SONGTROVE_USERNAME and "
            "SONGTROVE_PASSWORD_HASH to create the first admin, or run "
            "`python3 manage.py set-password` and restart the app."
        )

    now = _now()
    database.execute(
        """INSERT INTO users
               (username, password_hash, role, is_active, created_at,
                last_login_at, password_changed_at)
           VALUES (?, ?, ?, 1, ?, '', ?)""",
        (username, password_hash, ROLE_ADMIN, now, now),
    )


def _assign_orphan_songs(database: sqlite3.Connection) -> None:
    """Give migrated songs to the first admin so they remain reachable."""
    admin = database.execute(
        "SELECT id FROM users WHERE role = ? ORDER BY id ASC LIMIT 1",
        (ROLE_ADMIN,),
    ).fetchone()
    if not admin:
        return
    database.execute(
        """UPDATE songs SET owner_id = ?
            WHERE owner_id = 0 OR owner_id IS NULL""",
        (admin["id"],),
    )


def _migrate_users_schema(database: sqlite3.Connection) -> None:
    """Add the guest marker to user tables created before guest mode."""
    columns = {
        row["name"]
        for row in database.execute("PRAGMA table_info(users)").fetchall()
    }
    if columns and "is_guest" not in columns:
        database.execute(
            "ALTER TABLE users ADD COLUMN is_guest INTEGER NOT NULL DEFAULT 0"
        )


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
        database.execute("DROP INDEX IF EXISTS idx_songs_owner_created")
        database.execute(SONGS_TABLE)

        def text_column(name: str) -> str:
            return f"COALESCE({name}, '')" if name in columns else "''"

        if "tuning" in columns:
            tuning_expression = (
                "CASE WHEN TRIM(COALESCE(tuning, '')) = '' "
                "THEN ? ELSE tuning END"
            )
        else:
            tuning_expression = "?"

        database.execute(
            f"""INSERT INTO songs
                   (id, title, artist, content, notes, source_url, tags,
                    tuning, capo, rating, created_at, updated_at)
               SELECT id, title, artist, content,
                      {text_column('notes')},
                      {text_column('source_url')},
                      {text_column('tags')},
                      {tuning_expression},
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
