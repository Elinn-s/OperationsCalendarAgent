from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime

import psycopg2
import psycopg2.extras


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL", "")
        except Exception:
            pass
    if not url:
        raise RuntimeError("DATABASE_URL 未配置，请在 .streamlit/secrets.toml 或环境变量中设置。")
    return url


class _Conn:
    """使 psycopg2 的接口与原 sqlite3 用法保持兼容（execute/fetchall/fetchone）。"""

    def __init__(self, raw: psycopg2.extensions.connection) -> None:
        self._raw = raw
        self._cur = raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql: str, params=None):
        # sqlite3 用 ? 占位，psycopg2 用 %s
        self._cur.execute(sql.replace("?", "%s"), params)
        return self._cur

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._cur.close()
        self._raw.close()


@contextmanager
def get_conn():
    conn = _Conn(psycopg2.connect(_database_url()))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _next_system_no_for_date(conn: _Conn, target_date: date) -> str:
    prefix = f"NTC-{target_date.strftime('%Y%m%d')}-"
    rows = conn.execute(
        "SELECT system_no FROM notifications WHERE system_no LIKE ?",
        (f"{prefix}%",),
    ).fetchall()
    max_seq = 0
    for row in rows:
        try:
            max_seq = max(max_seq, int(str(row["system_no"]).rsplit("-", 1)[-1]))
        except (TypeError, ValueError):
            continue
    return f"{prefix}{max_seq + 1:04d}"


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                notification_id TEXT UNIQUE NOT NULL,
                doc_ref TEXT,
                system_no TEXT,
                notice_type TEXT DEFAULT '其他',
                department TEXT,
                drafter TEXT,
                reviewer TEXT,
                approver TEXT,
                title TEXT,
                purpose TEXT,
                target_scope TEXT,
                effective_start TEXT,
                effective_end TEXT,
                archive_until TEXT,
                contacts TEXT,
                status TEXT DEFAULT '执行中',
                tags TEXT DEFAULT '[]',
                file_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                variables TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id SERIAL PRIMARY KEY,
                notification_id TEXT,
                action TEXT NOT NULL,
                detail TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                activity_name TEXT NOT NULL,
                notification_content TEXT,
                planned_publish_date TEXT,
                make_reminder_date TEXT,
                publish_reminder_date TEXT,
                effective_start TEXT,
                effective_end TEXT,
                owner TEXT,
                status TEXT DEFAULT '已预录',
                remind_14d_sent INTEGER DEFAULT 0,
                remind_7d_sent INTEGER DEFAULT 0,
                linked_notification_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # 安全新增列（PostgreSQL 支持 IF NOT EXISTS）
        for ddl in [
            "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notice_type TEXT DEFAULT '其他'",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS notification_content TEXT",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS make_reminder_date TEXT",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS publish_reminder_date TEXT",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS status TEXT DEFAULT '待发布'",
            "ALTER TABLE plans ADD COLUMN IF NOT EXISTS updated_at TEXT",
        ]:
            conn.execute(ddl)

        # 状态规范化
        conn.execute("UPDATE notifications SET status = '执行中' WHERE status IN ('已发布', '草稿', '待审批', '待发布')")
        conn.execute("UPDATE notifications SET status = '已截止' WHERE status IN ('已过期', '已归档')")
        conn.execute("UPDATE plans SET status = '待发布' WHERE status IN ('未开始', '制定中')")
        conn.execute(
            "UPDATE notifications SET status = '已截止'"
            " WHERE status = '执行中' AND effective_end IS NOT NULL AND effective_end < ?",
            (date.today().isoformat(),),
        )
        conn.execute("UPDATE notifications SET notice_type = '其他' WHERE notice_type IS NULL OR notice_type = ''")

        # 补全缺失 system_no
        missing = conn.execute(
            "SELECT id, created_at FROM notifications WHERE system_no IS NULL OR system_no = '' ORDER BY created_at, id"
        ).fetchall()
        for row in missing:
            created_at = row["created_at"] or date.today().isoformat()
            try:
                target_date = date.fromisoformat(str(created_at)[:10])
            except ValueError:
                target_date = date.today()
            conn.execute(
                "UPDATE notifications SET system_no = ? WHERE id = ?",
                (_next_system_no_for_date(conn, target_date), row["id"]),
            )


def new_id() -> str:
    return str(uuid.uuid4())


def generate_system_no() -> str:
    with get_conn() as conn:
        return _next_system_no_for_date(conn, date.today())


def log_action(notification_id: str, action: str, detail: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (notification_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
            (notification_id, action, detail, datetime.now().isoformat()),
        )
