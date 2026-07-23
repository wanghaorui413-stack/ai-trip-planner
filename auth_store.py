"""SQLite persistence and token authentication for user-owned travel plans."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


logger = logging.getLogger(__name__)
DB_PATH = Path(os.getenv("APP_DB_PATH", "data/trip_planner.db"))
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
AUTH_SECRET = os.getenv("AUTH_SECRET", "change-me-in-production")
PBKDF2_ITERATIONS = 310_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_database() -> None:
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                preferences_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saved_trips (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                destination TEXT NOT NULL,
                days INTEGER NOT NULL,
                preferences TEXT NOT NULL DEFAULT '',
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_saved_trips_user_updated
            ON saved_trips(user_id, updated_at DESC);
            """
        )
    if AUTH_SECRET == "change-me-in-production":
        logger.warning("AUTH_SECRET is using the development default; set it in production.")


def _password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _public_user(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "preferences": json.loads(row["preferences_json"] or "{}"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_user(email: str, display_name: str, password: str) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    salt = secrets.token_bytes(16)
    timestamp = _now()
    try:
        with _connection() as connection:
            connection.execute(
                """INSERT INTO users
                (id, email, display_name, password_hash, password_salt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, email.strip().lower(), display_name.strip(),
                 _encode(_password_digest(password, salt)), _encode(salt), timestamp, timestamp),
            )
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise ValueError("该邮箱已注册") from exc
    return _public_user(row)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
        ).fetchone()
    if row is None:
        return None
    actual = _password_digest(password, _decode(row["password_salt"]))
    if not hmac.compare_digest(actual, _decode(row["password_hash"])):
        return None
    return _public_user(row)


def create_access_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    encoded_payload = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{_encode(signature)}"


def user_from_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected = hmac.new(
            AUTH_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _decode(encoded_signature)):
            return None
        payload = json.loads(_decode(encoded_payload))
        if int(payload["exp"]) < int(time.time()):
            return None
        user_id = str(payload["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    with _connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row) if row else None


def update_user(user_id: str, display_name: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
    with _connection() as connection:
        connection.execute(
            "UPDATE users SET display_name = ?, preferences_json = ?, updated_at = ? WHERE id = ?",
            (display_name.strip(), json.dumps(preferences, ensure_ascii=False), _now(), user_id),
        )
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise ValueError("用户不存在")
    return _public_user(row)


def _trip_summary(row: sqlite3.Row, include_plan: bool = False) -> Dict[str, Any]:
    result = {
        "id": row["id"], "title": row["title"], "destination": row["destination"],
        "days": row["days"], "preferences": row["preferences"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }
    if include_plan:
        result["plan"] = json.loads(row["plan_json"])
    return result


def save_trip(user_id: str, title: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    trip_id = str(uuid.uuid4())
    timestamp = _now()
    destination = str(plan.get("destination") or "未命名目的地")[:120]
    try:
        days = max(1, int(plan.get("days") or 1))
    except (TypeError, ValueError):
        days = 1
    preferences = str(plan.get("preferences") or "")[:2000]
    with _connection() as connection:
        connection.execute(
            """INSERT INTO saved_trips
            (id, user_id, title, destination, days, preferences, plan_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (trip_id, user_id, title.strip()[:120] or f"{destination} {days}日攻略",
             destination, days, preferences, json.dumps(plan, ensure_ascii=False), timestamp, timestamp),
        )
        row = connection.execute("SELECT * FROM saved_trips WHERE id = ?", (trip_id,)).fetchone()
    return _trip_summary(row, include_plan=True)


def list_trips(user_id: str) -> List[Dict[str, Any]]:
    with _connection() as connection:
        rows = connection.execute(
            "SELECT * FROM saved_trips WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)
        ).fetchall()
    return [_trip_summary(row) for row in rows]


def get_trip(user_id: str, trip_id: str) -> Optional[Dict[str, Any]]:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM saved_trips WHERE id = ? AND user_id = ?", (trip_id, user_id)
        ).fetchone()
    return _trip_summary(row, include_plan=True) if row else None


def delete_trip(user_id: str, trip_id: str) -> bool:
    with _connection() as connection:
        cursor = connection.execute(
            "DELETE FROM saved_trips WHERE id = ? AND user_id = ?", (trip_id, user_id)
        )
    return cursor.rowcount > 0
