#!/usr/bin/env python3
"""Manage Songtrove passwords, environment, and user accounts."""

from __future__ import annotations

import argparse
import getpass
import os
import secrets
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "hash-password",
        help="print a password hash for a hosting provider's environment variables",
    )
    subparsers.add_parser(
        "set-password",
        help="save the first-run bootstrap password in the local .env file",
    )
    subparsers.add_parser(
        "list-users",
        help="list accounts in the configured database",
    )

    create_user = subparsers.add_parser(
        "create-user",
        help="create an account in the configured database",
    )
    create_user.add_argument("username")
    create_user.add_argument(
        "--role",
        choices=("member", "admin"),
        default="member",
        help="role for the new account (default: member)",
    )

    reset_password = subparsers.add_parser(
        "reset-password",
        help="replace an account password in the configured database",
    )
    reset_password.add_argument("username")

    args = parser.parse_args()
    if args.command == "hash-password":
        print(generate_password_hash(_prompt_password()))
    elif args.command == "set-password":
        _set_password()
    elif args.command == "list-users":
        _list_users()
    elif args.command == "create-user":
        _create_user(args.username, args.role)
    elif args.command == "reset-password":
        _reset_password(args.username)


def _prompt_password() -> str:
    password = getpass.getpass("New password: ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")
    if len(password) > 200:
        raise SystemExit("Keep the password under 200 characters.")
    confirmation = getpass.getpass("Repeat password: ")
    if password != confirmation:
        raise SystemExit("The passwords do not match.")
    return password


def _set_password() -> None:
    password_hash = generate_password_hash(_prompt_password())
    existing = _read_env()
    values = {
        "SONGTROVE_USERNAME": os.environ.get("SONGTROVE_USERNAME")
        or existing.get("SONGTROVE_USERNAME")
        or "songtrove",
        "SONGTROVE_PASSWORD_HASH": password_hash,
    }
    if not (os.environ.get("SECRET_KEY") or existing.get("SECRET_KEY")):
        values["SECRET_KEY"] = secrets.token_hex(32)
    if not (os.environ.get("SONGTROVE_DB") or existing.get("SONGTROVE_DB")):
        values["SONGTROVE_DB"] = str(BASE_DIR / "data" / "songtrove.db")
    if not (
        os.environ.get("SONGTROVE_SECURE_COOKIES")
        or existing.get("SONGTROVE_SECURE_COOKIES")
    ):
        values["SONGTROVE_SECURE_COOKIES"] = "0"

    _write_env(existing, values)
    print(f"Updated {ENV_PATH}")
    print("Restart the app to use the new password.")
    print(
        "This bootstrap password only creates the first admin. If accounts "
        "already exist, use `python3 manage.py reset-password USERNAME`."
    )


def _management_app():
    from app import app

    return app


def _list_users() -> None:
    import db

    app = _management_app()
    with app.app_context():
        users = db.list_users()
        if not users:
            print("No users.")
            return
        print(f"{'ID':>4}  {'USERNAME':<24} {'ROLE':<7} {'STATUS':<8} LAST LOGIN")
        for user in users:
            status = "active" if user["is_active"] else "disabled"
            last_login = user["last_login_at"] or "never"
            print(
                f"{user['id']:>4}  {user['username']:<24} "
                f"{user['role']:<7} {status:<8} {last_login}"
            )


def _create_user(username: str, role: str) -> None:
    import db
    from app import USERNAME_RE

    username = username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise SystemExit(
            "Use 3–32 letters, numbers, dots, dashes or underscores, "
            "starting with a letter or number."
        )

    password_hash = generate_password_hash(_prompt_password())
    app = _management_app()
    with app.app_context():
        try:
            db.create_user(
                username=username, password_hash=password_hash, role=role
            )
        except db.UsernameTaken:
            raise SystemExit(f"Username “{username}” is already in use.") from None
    print(f"Created {role} account “{username}”.")


def _reset_password(username: str) -> None:
    import db

    app = _management_app()
    with app.app_context():
        user = db.get_user_by_username(username)
        if user is None:
            raise SystemExit(f"No account named “{username}”.")
        db.set_user_password(user["id"], generate_password_hash(_prompt_password()))
    print(f"Reset the password for “{user['username']}”.")



def _read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _write_env(existing: dict[str, str], updates: dict[str, str]) -> None:
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    pending = dict(updates)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key in pending:
            lines[index] = f"{key}={pending.pop(key)}"

    if pending:
        if lines and lines[-1].strip():
            lines.append("")
        for key, value in pending.items():
            lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    try:
        ENV_PATH.chmod(0o600)
    except OSError:
        pass


if __name__ == "__main__":
    main()
