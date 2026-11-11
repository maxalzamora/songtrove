#!/usr/bin/env python3
"""Create the password hash and local environment file for Songtrove."""

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
        help="prompt for a password and save it to the local .env file",
    )

    args = parser.parse_args()
    if args.command == "hash-password":
        print(generate_password_hash(_prompt_password()))
    else:
        _set_password()


def _prompt_password() -> str:
    password = getpass.getpass("New password: ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")
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
