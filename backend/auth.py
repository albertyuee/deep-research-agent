"""Local authentication and document authorization for the first permissions release.

The service intentionally uses only the Python standard library so it works in a
fresh checkout.  SQLite is the local adapter; the tables and policy helpers are
kept small enough to migrate to Supabase/PostgreSQL later without changing the
HTTP contract.

Set ``AUTH_ENABLED=true`` to require a bearer token.  When it is disabled the
legacy single-user behaviour is preserved through a synthetic administrator.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, Query, status

from config.settings import settings


PERMISSIONS = {
    "admin": frozenset({
        "document:read", "document:upload", "document:update", "document:delete",
        "document:share", "document:approve", "research:create", "research:read",
        "research:cancel", "settings:read", "settings:update", "user:manage",
    }),
    "researcher": frozenset({
        "document:read", "document:upload", "document:update", "document:delete",
        "research:create", "research:read", "research:cancel", "settings:read",
    }),
    "guest": frozenset({"document:read", "research:create", "research:read"}),
}


@dataclass(frozen=True)
class User:
    id: str
    email: str
    display_name: str
    role: str
    department_id: str | None = None
    active: bool = True

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


SYSTEM_USER = User("system", "system@local", "系统管理员", "admin")


def _db_path() -> Path:
    configured = os.getenv("AUTH_DB_PATH", "data/auth.db")
    path = Path(configured)
    if not path.is_absolute():
        path = settings.project_root / path
    return path


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_auth_db() -> None:
    """Create the local auth schema and optional bootstrap administrator."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                parent_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'researcher', 'guest')),
                department_id TEXT REFERENCES departments(id) ON DELETE SET NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS document_permissions (
                document_id TEXT NOT NULL,
                subject_type TEXT NOT NULL CHECK (subject_type IN ('user', 'role', 'department')),
                subject_id TEXT NOT NULL,
                permission TEXT NOT NULL DEFAULT 'read',
                PRIMARY KEY (document_id, subject_type, subject_id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_doc_permissions_doc ON document_permissions(document_id);
            """
        )

        email = os.getenv("AUTH_ADMIN_EMAIL", "").strip().lower()
        password = os.getenv("AUTH_ADMIN_PASSWORD", "")
        if email and password:
            existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not existing:
                now = _now()
                conn.execute(
                    "INSERT INTO users (id,email,display_name,password_hash,role,created_at) VALUES (?,?,?,?,?,?)",
                    (uuid.uuid4().hex, email, os.getenv("AUTH_ADMIN_NAME", "系统管理员"), _hash_password(password), "admin", now),
                )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def authenticate(email: str, password: str) -> tuple[User, str] | None:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email)=lower(?) AND active=1", (email.strip(),)).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            return None
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        conn.execute(
            "INSERT INTO sessions (token_hash,user_id,expires_at,created_at) VALUES (?,?,?,?)",
            (_token_hash(token), row["id"], expires.isoformat(), _now()),
        )
        return _row_to_user(row), token


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _row_to_user(row: sqlite3.Row) -> User:
    return User(row["id"], row["email"], row["display_name"], row["role"], row["department_id"], bool(row["active"]))


def get_user_by_token(token: str) -> User | None:
    init_auth_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>? AND u.active=1",
            (_token_hash(token), _now()),
        ).fetchone()
        return _row_to_user(row) if row else None


def current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None, alias="access_token"),
) -> User:
    if not os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        return SYSTEM_USER
    token = access_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    user = get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    return user


def require_permission(permission: str) -> Callable[..., User]:
    def dependency(user: User = Depends(current_user)) -> User:
        if permission not in PERMISSIONS.get(user.role, frozenset()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"没有权限：{permission}")
        return user

    return dependency


def can_access_document(user: User, metadata: dict[str, Any]) -> bool:
    """Evaluate document visibility against a user and its ACL metadata."""
    if user.is_admin or not os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        return True
    if str(metadata.get("owner_id", "")) == user.id:
        return True
    visibility = metadata.get("visibility", "private")
    if visibility == "public":
        return True
    if visibility == "workspace":
        return True
    if visibility == "department" and metadata.get("department_id") and metadata.get("department_id") == user.department_id:
        return True
    if visibility == "departments" and user.department_id in _as_list(metadata.get("allowed_departments")):
        return True
    if visibility == "roles" and user.role in _as_list(metadata.get("allowed_roles")):
        return True
    if visibility == "users" and user.id in _as_list(metadata.get("allowed_users")):
        return True
    return _acl_allows(user, str(metadata.get("upload_id", "")))


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [item for item in value.split(",") if item]
    return []


def _acl_allows(user: User, document_id: str) -> bool:
    if not document_id:
        return False
    init_auth_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT subject_type, subject_id FROM document_permissions WHERE document_id=? AND permission='read'",
            (document_id,),
        ).fetchall()
    return any(
        (row["subject_type"] == "user" and row["subject_id"] == user.id)
        or (row["subject_type"] == "role" and row["subject_id"] == user.role)
        or (row["subject_type"] == "department" and row["subject_id"] == user.department_id)
        for row in rows
    )


def allowed_upload_ids(user: User, files: list[dict]) -> set[str] | None:
    """Return a retrieval allow-list; None means no filtering in legacy mode."""
    if not os.getenv("AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        return None
    return {str(item["id"]) for item in files if can_access_document(user, item)}
