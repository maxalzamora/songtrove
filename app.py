"""A small, self-hosted guitar library for chords and lyrics."""

from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash

import db
from render import chord_sheet_html, merge_edited_text, plain_sheet_text

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    username, password_hash = _load_auth_config()
    app.config.update(
        SECRET_KEY=_load_secret_key(),
        DATABASE=database_path
        or os.environ.get("SONGTROVE_DB", str(DATA_DIR / "songtrove.db")),
        MAX_CONTENT_LENGTH=256 * 1024,
        SONGTROVE_USERNAME=username,
        SONGTROVE_PASSWORD_HASH=password_hash,
        SESSION_COOKIE_NAME="songtrove_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_flag("SONGTROVE_SECURE_COOKIES"),
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        LOGIN_FAILURE_DELAY=0.4,
    )
    CSRFProtect(app)
    db.init_app(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        if _wants_json():
            return jsonify(ok=False, error="Your session expired."), 400
        flash("Your session expired. Please try again.", "error")
        return redirect(url_for("login"))

    @app.before_request
    def require_login():
        if request.endpoint in {"login", "static", "healthz"}:
            return None
        if request.endpoint is None:
            return None
        if session.get("authenticated"):
            return None
        if _wants_json():
            return jsonify(ok=False, error="Please log in again."), 401
        next_url = request.path
        if request.query_string:
            next_url += "?" + request.query_string.decode()
        return redirect(url_for("login", next=next_url))

    @app.get("/healthz")
    def healthz():
        db.get_db().execute("SELECT 1").fetchone()
        return jsonify(ok=True)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("authenticated"):
            return redirect(url_for("index"))

        next_url = _safe_next_url(
            request.args.get("next") or request.form.get("next", "")
        )
        error = None
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            valid_username = hmac.compare_digest(
                username, app.config["SONGTROVE_USERNAME"]
            )
            valid_password = check_password_hash(
                app.config["SONGTROVE_PASSWORD_HASH"], password
            )
            if valid_username and valid_password:
                session.clear()
                session["authenticated"] = True
                session.permanent = True
                return redirect(next_url or url_for("index"))

            app.logger.warning("Failed login attempt")
            delay = app.config["LOGIN_FAILURE_DELAY"]
            if delay:
                time.sleep(delay)
            error = "Wrong username or password."

        return render_template(
            "login.html", error=error, next=next_url or ""
        )

    @app.post("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        query = request.args.get("q", "").strip()
        sort = request.args.get("sort", "recent")
        if sort not in db.SORT_ORDERS:
            sort = "recent"

        available_tags = db.list_tags()
        tag = request.args.get("tag", "").strip().lstrip("#").casefold()

        rating = request.args.get("rating", "").strip()
        if rating not in {"", "0", "3", "4", "5"}:
            rating = ""

        available_tunings = db.list_tunings()
        tuning = request.args.get("tuning", "").strip()

        songs = db.list_songs(
            query, sort, tag=tag, rating=rating, tuning=tuning
        )
        return render_template(
            "index.html",
            songs=songs,
            total=db.count_songs(),
            query=query,
            sort=sort,
            tag=tag,
            rating=rating,
            tuning=tuning,
            tags=available_tags,
            tunings=available_tunings,
            has_filters=bool(query or tag or rating or tuning),
        )

    @app.route("/songs/new", methods=["GET", "POST"])
    def new_song():
        form = _empty_song_form()
        if request.method == "POST":
            form = _song_form_from_request()
            errors = _song_form_errors(form)

            if errors:
                return (
                    render_template("new_song.html", form=form, errors=errors),
                    400,
                )

            song_id = db.add_manual_song(
                title=form["title"],
                artist=form["artist"],
                content=form["content"],
                notes=form["notes"],
                source_url=_normalize_source_url(form["source_url"])[0],
                tags=form["tags"],
                tuning=form["tuning"],
                capo=form["capo"],
                rating=form["rating"],
            )
            flash(f"Added “{form['title']}”.", "success")
            return redirect(url_for("song_detail", song_id=song_id))

        return render_template("new_song.html", form=form, errors=[])

    @app.get("/song/<int:song_id>")
    def song_detail(song_id: int):
        song = db.get_song(song_id) or abort(404)
        # The capo is a transposition control: chords are shown as the shapes
        # to play with that capo, so the song keeps its original concert pitch.
        capo = _clamp(song["capo"], 0, 12, 0)
        return render_template(
            "song.html",
            song=song,
            sheet_html=chord_sheet_html(song["content"], transpose=-capo),
        )

    @app.get("/song/<int:song_id>/edit")
    def edit_song(song_id: int):
        song = db.get_song(song_id) or abort(404)
        return render_template(
            "edit_song.html",
            song=song,
            form=_song_form_from_song(song),
            errors=[],
        )

    @app.post("/song/<int:song_id>/edit")
    def save_song(song_id: int):
        song = db.get_song(song_id) or abort(404)
        form = _song_form_from_request()
        errors = _song_form_errors(form)
        if errors:
            return (
                render_template(
                    "edit_song.html", song=song, form=form, errors=errors
                ),
                400,
            )

        db.update_song(
            song_id,
            title=form["title"],
            artist=form["artist"],
            content=merge_edited_text(song["content"], form["content"]),
            notes=form["notes"],
            source_url=_normalize_source_url(form["source_url"])[0],
            tags=form["tags"],
            tuning=form["tuning"],
            capo=form["capo"],
            rating=form["rating"],
        )
        flash(f"Saved “{form['title']}”.", "success")
        return redirect(url_for("song_detail", song_id=song_id))

    @app.post("/song/<int:song_id>/update")
    def update_song(song_id: int):
        song = db.get_song(song_id) or abort(404)
        capo = None
        rating = None
        if "capo" in request.form:
            capo = _clamp(request.form.get("capo"), 0, 12, 0)
        if "rating" in request.form:
            rating = _clamp(request.form.get("rating"), 0, 5, 0)

        db.update_settings(song_id, capo=capo, rating=rating)

        if _wants_json():
            return jsonify(
                ok=True,
                song_id=song["id"],
                capo=capo if capo is not None else song["capo"],
                rating=rating if rating is not None else song["rating"],
            )
        flash("Saved your changes.", "success")
        return redirect(url_for("song_detail", song_id=song_id))

    @app.post("/song/<int:song_id>/delete")
    def delete_song(song_id: int):
        song = db.get_song(song_id) or abort(404)
        db.delete_song(song_id)
        flash(f"Removed “{song['title']}” from your library.", "info")
        return redirect(url_for("index"))

    @app.get("/export")
    def export_songs():
        songs = [dict(song) for song in db.list_songs("", "recent")]
        payload = json.dumps({"songs": songs}, indent=2, ensure_ascii=False)
        return Response(
            payload,
            mimetype="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="songtrove.json"'
            },
        )

    @app.route("/import", methods=["GET", "POST"])
    def import_songs():
        errors = []
        if request.method == "POST":
            upload = request.files.get("backup")
            if not upload or not upload.filename:
                errors.append("Choose a JSON file exported from this library.")
            else:
                try:
                    payload = json.loads(upload.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append("That file is not valid JSON.")
                else:
                    songs = payload.get("songs") if isinstance(payload, dict) else None
                    if not isinstance(songs, list) or not songs:
                        errors.append("That file does not contain any songs.")
                    elif len(songs) > 1000:
                        errors.append("That file contains too many songs.")
                    else:
                        imported = []
                        for index, item in enumerate(songs, start=1):
                            if not isinstance(item, dict):
                                errors.append(f"Song {index} is not an object.")
                                continue
                            title = str(item.get("title") or "").strip()
                            artist = str(item.get("artist") or "").strip()
                            content = (
                                str(item.get("content") or "")
                                .replace("\r\n", "\n")
                                .replace("\r", "\n")
                            )
                            if not title or not artist or not content.strip():
                                errors.append(
                                    f"Song {index} needs a title, artist and sheet."
                                )
                                continue
                            notes = (
                                str(item.get("notes") or "")
                                .replace("\r\n", "\n")
                                .replace("\r", "\n")
                                .strip()
                            )
                            if len(notes) > 5000:
                                errors.append(
                                    f"Song {index} has notes that are too long."
                                )
                                continue
                            source_url, source_error = _normalize_source_url(
                                item.get("source_url") or ""
                            )
                            if source_error:
                                errors.append(
                                    f"Song {index} has an invalid source URL."
                                )
                                continue
                            tags = db.normalize_tags(item.get("tags") or "")
                            if len(tags) > 300:
                                errors.append(
                                    f"Song {index} has too many tags."
                                )
                                continue
                            imported.append(
                                {
                                    "title": title,
                                    "artist": artist,
                                    "content": content,
                                    "notes": notes,
                                    "source_url": source_url,
                                    "tags": tags,
                                    "tuning": str(
                                        item.get("tuning") or db.DEFAULT_TUNING
                                    ).strip()
                                    or db.DEFAULT_TUNING,
                                    "capo": _clamp(item.get("capo"), 0, 12, 0),
                                    "rating": _clamp(item.get("rating"), 0, 5, 0),
                                }
                            )

                        if not errors:
                            for song in imported:
                                db.add_manual_song(**song)
                            flash(
                                f"Imported {len(imported)} "
                                f"song{'s' if len(imported) != 1 else ''}.",
                                "success",
                            )
                            return redirect(url_for("index"))

            if errors:
                return (
                    render_template("import_songs.html", errors=errors),
                    400,
                )

        return render_template("import_songs.html", errors=[])

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "error.html",
                code=404,
                message="We couldn't find that page. It may have been removed.",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(_error):
        return (
            render_template(
                "error.html",
                code=500,
                message="Something went wrong on our side. Try again.",
            ),
            500,
        )

    @app.template_filter("pretty_date")
    def pretty_date(value: str) -> str:
        try:
            date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except (TypeError, ValueError):
            return ""
        return date.strftime("%d %b %Y")

    @app.template_filter("tuning_label")
    def tuning_label(value: str) -> str:
        tuning = (value or "").strip()
        if not tuning or tuning == db.DEFAULT_TUNING:
            return "Standard"
        return tuning

    @app.template_filter("tag_list")
    def tag_list(value) -> list[str]:
        return db.parse_tags(value)

    return app


def _empty_song_form() -> dict[str, str | int]:
    return {
        "title": "",
        "artist": "",
        "tuning": db.DEFAULT_TUNING,
        "capo": 0,
        "rating": 0,
        "notes": "",
        "source_url": "",
        "tags": "",
        "content": "",
    }


def _song_form_from_song(song) -> dict[str, str | int]:
    return {
        "title": song["title"],
        "artist": song["artist"],
        "tuning": song["tuning"] or db.DEFAULT_TUNING,
        "capo": song["capo"],
        "rating": song["rating"],
        "notes": song["notes"] or "",
        "source_url": song["source_url"] or "",
        "tags": " ".join(f"#{tag}" for tag in db.parse_tags(song["tags"])),
        "content": plain_sheet_text(song["content"]),
    }


def _song_form_from_request() -> dict[str, str | int]:
    content = request.form.get("content", "")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    notes = request.form.get("notes", "")
    notes = notes.replace("\r\n", "\n").replace("\r", "\n")
    return {
        "title": request.form.get("title", "").strip(),
        "artist": request.form.get("artist", "").strip(),
        "tuning": request.form.get("tuning", "").strip() or db.DEFAULT_TUNING,
        "capo": _clamp(request.form.get("capo"), 0, 12, 0),
        "rating": _clamp(request.form.get("rating"), 0, 5, 0),
        "notes": notes,
        "source_url": request.form.get("source_url", "").strip(),
        "tags": request.form.get("tags", "").strip(),
        "content": content,
    }


def _song_form_errors(form: dict[str, str | int]) -> list[str]:
    errors = []
    if not form["title"]:
        errors.append("Add a title.")
    if not form["artist"]:
        errors.append("Add an artist.")
    if not str(form["content"]).strip():
        errors.append("Add the chords or lyrics.")
    if len(str(form["notes"])) > 5000:
        errors.append("Keep notes under 5,000 characters.")
    if len(str(form["source_url"])) > 500:
        errors.append("Keep the source URL under 500 characters.")
    if len(str(form["tags"])) > 300:
        errors.append("Keep tags under 300 characters.")
    _, source_error = _normalize_source_url(form["source_url"])
    if source_error:
        errors.append(source_error)
    return errors


def _normalize_source_url(value) -> tuple[str, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return "", None

    if "://" in raw:
        candidate = raw
    else:
        if ":" in raw.split("/", 1)[0]:
            return raw, "Add a valid http:// or https:// source URL."
        candidate = f"https://{raw}"

    if any(character.isspace() for character in candidate):
        return raw, "Use a source URL without spaces."
    try:
        parsed = urlsplit(candidate)
        parsed.port
    except ValueError:
        return raw, "Add a valid http:// or https:// source URL."
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or not parsed.netloc
    ):
        return raw, "Add a valid http:// or https:// source URL."
    return candidate, None


def _load_secret_key() -> str:
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / ".secret_key"
    if path.exists():
        key = path.read_text(encoding="utf-8").strip()
        if key:
            return key

    key = secrets.token_hex(32)
    path.write_text(key, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return key


def _load_auth_config() -> tuple[str, str]:
    username = (
        os.environ.get("SONGTROVE_USERNAME", "songtrove").strip() or "songtrove"
    )
    password_hash = os.environ.get("SONGTROVE_PASSWORD_HASH", "").strip()
    if not password_hash:
        raise RuntimeError(
            "SONGTROVE_PASSWORD_HASH is not set. Run "
            "`python3 manage.py set-password` for local use, or set the "
            "environment variable in your host's dashboard."
        )
    return username, password_hash


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_next_url(target: str) -> str | None:
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target


def _clamp(value, low: int, high: int, fallback: int) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def _wants_json() -> bool:
    return "application/json" in request.headers.get("Accept", "")


# Used by `flask run` and `python app.py`.
app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
