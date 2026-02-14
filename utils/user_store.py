"""简单持久化用户存储（SQLite）"""
import os
import json
import sqlite3
import threading
from typing import Optional, Dict, List
from datetime import datetime


class UserStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("USER_DB_PATH", "data/users.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        display_name TEXT,
                        roles TEXT,
                        permissions TEXT,
                        password_hash TEXT NOT NULL,
                        created_at TEXT,
                        updated_at TEXT,
                        is_active INTEGER DEFAULT 1
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def _row_to_user(self, row) -> Optional[Dict]:
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "displayName": row[3],
            "roles": json.loads(row[4]) if row[4] else [],
            "permissions": json.loads(row[5]) if row[5] else [],
            "password_hash": row[6],
            "createdAt": row[7],
            "updatedAt": row[8],
            "isActive": bool(row[9]),
        }

    def get_by_username(self, username: str) -> Optional[Dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, username, email, display_name, roles, permissions, password_hash, created_at, updated_at, is_active FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return self._row_to_user(row)
        finally:
            conn.close()

    def get_by_email(self, email: str) -> Optional[Dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, username, email, display_name, roles, permissions, password_hash, created_at, updated_at, is_active FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            return self._row_to_user(row)
        finally:
            conn.close()

    def get_by_id(self, user_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, username, email, display_name, roles, permissions, password_hash, created_at, updated_at, is_active FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return self._row_to_user(row)
        finally:
            conn.close()

    def list_users(self) -> List[Dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id, username, email, display_name, roles, permissions, password_hash, created_at, updated_at, is_active FROM users"
            ).fetchall()
            return [self._row_to_user(row) for row in rows]
        finally:
            conn.close()

    def create_user(self, user: Dict) -> None:
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO users (id, username, email, display_name, roles, permissions, password_hash, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    user["username"],
                    user.get("email"),
                    user.get("displayName"),
                    json.dumps(user.get("roles", []), ensure_ascii=False),
                    json.dumps(user.get("permissions", []), ensure_ascii=False),
                    user["password_hash"],
                    user.get("createdAt", now),
                    user.get("updatedAt", now),
                    1 if user.get("isActive", True) else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_user(self, user_id: str, updates: Dict) -> Optional[Dict]:
        user = self.get_by_id(user_id)
        if not user:
            return None

        user.update(updates)
        user["updatedAt"] = datetime.utcnow().isoformat()

        conn = self._get_conn()
        try:
            conn.execute(
                """
                UPDATE users
                SET email = ?, display_name = ?, roles = ?, permissions = ?, password_hash = ?, updated_at = ?, is_active = ?
                WHERE id = ?
                """,
                (
                    user.get("email"),
                    user.get("displayName"),
                    json.dumps(user.get("roles", []), ensure_ascii=False),
                    json.dumps(user.get("permissions", []), ensure_ascii=False),
                    user.get("password_hash"),
                    user.get("updatedAt"),
                    1 if user.get("isActive", True) else 0,
                    user_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return user

    def delete_user(self, user_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
