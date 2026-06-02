from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def _secret(key: str, default: str = "") -> str:
    value = os.environ.get(key, default)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default


def _database_mode() -> str:
    return _secret("APP_DATABASE_MODE", "sqlite").strip().lower()


def _database_url() -> str:
    url = _secret("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 未配置，请在 .streamlit/secrets.toml 或环境变量中设置。")
    return url


def _sqlite_path() -> Path:
    raw_path = _secret("SQLITE_PATH", "data/app.db")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class _PostgresConn:
    """使 psycopg2 的接口与原 sqlite3 用法保持兼容（execute/fetchall/fetchone）。"""

    def __init__(self, raw: psycopg2.extensions.connection) -> None:
        self._raw = raw
        self._cur = raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.dialect = "postgres"

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


class _SqliteConn:
    def __init__(self, raw: sqlite3.Connection) -> None:
        self._raw = raw
        self._raw.row_factory = sqlite3.Row
        self.dialect = "sqlite"

    def execute(self, sql: str, params=None):
        return self._raw.execute(sql, params or ())

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


@contextmanager
def get_conn():
    if _database_mode() == "postgres":
        conn = _PostgresConn(psycopg2.connect(_database_url()))
    else:
        conn = _SqliteConn(sqlite3.connect(_sqlite_path()))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _pk(conn) -> str:
    if conn.dialect == "postgres":
        return "SERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def _add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    if conn.dialect == "postgres":
        conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        return

    columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row["name"] for row in columns}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _next_system_no_for_date(conn, target_date: date) -> str:
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
        pk = _pk(conn)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id {pk},
                notification_id TEXT UNIQUE NOT NULL,
                doc_ref TEXT,
                system_no TEXT,
                notice_type TEXT DEFAULT '其他',
                issuer TEXT,
                owner TEXT,
                owner_role TEXT,
                department TEXT,
                drafter TEXT,
                reviewer TEXT,
                approver TEXT,
                title TEXT,
                description TEXT,
                purpose TEXT,
                target_scope TEXT,
                impact_store TEXT,
                impact_region TEXT,
                impact_role TEXT,
                deadline TEXT,
                effective_start TEXT,
                effective_end TEXT,
                archive_until TEXT,
                contacts TEXT,
                status TEXT DEFAULT '已发送',
                tags TEXT DEFAULT '[]',
                file_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id {pk},
                name TEXT NOT NULL,
                description TEXT,
                content TEXT NOT NULL,
                variables TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id {pk},
                notification_id TEXT,
                action TEXT NOT NULL,
                detail TEXT,
                actor TEXT DEFAULT '系统',
                timestamp TEXT NOT NULL
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id {pk},
                activity_name TEXT NOT NULL,
                notification_content TEXT,
                planned_publish_date TEXT,
                make_reminder_date TEXT,
                publish_reminder_date TEXT,
                effective_start TEXT,
                effective_end TEXT,
                owner TEXT,
                reminder_email TEXT,
                reminder_enabled INTEGER DEFAULT 1,
                status TEXT DEFAULT '已预录',
                remind_14d_sent INTEGER DEFAULT 0,
                remind_7d_sent INTEGER DEFAULT 0,
                linked_notification_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ack_recipients (
                id {pk},
                notification_id TEXT NOT NULL,
                department TEXT,
                recipient_name TEXT,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT '未发送',
                sent_at TEXT,
                confirmed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_log (
                id {pk},
                notification_id TEXT,
                ack_recipient_id INTEGER,
                recipient_email TEXT,
                subject TEXT,
                status TEXT NOT NULL,
                error TEXT,
                sent_at TEXT NOT NULL
            )
        """.format(pk=pk))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminder_log (
                id {pk},
                notification_id TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                reminder_date TEXT NOT NULL,
                recipient_email TEXT,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """.format(pk=pk))

        for table, column, definition in [
            ("audit_log", "actor", "TEXT DEFAULT '系统'"),
            ("notifications", "notice_type", "TEXT DEFAULT '其他'"),
            ("notifications", "issuer", "TEXT"),
            ("notifications", "owner", "TEXT"),
            ("notifications", "owner_role", "TEXT"),
            ("notifications", "description", "TEXT"),
            ("notifications", "impact_store", "TEXT"),
            ("notifications", "impact_region", "TEXT"),
            ("notifications", "impact_role", "TEXT"),
            ("notifications", "deadline", "TEXT"),
            ("plans", "notification_content", "TEXT"),
            ("plans", "make_reminder_date", "TEXT"),
            ("plans", "publish_reminder_date", "TEXT"),
            ("plans", "status", "TEXT DEFAULT '已预录'"),
            ("plans", "updated_at", "TEXT"),
            ("plans", "reminder_email", "TEXT"),
            ("plans", "reminder_enabled", "INTEGER DEFAULT 1"),
            ("ack_recipients", "department", "TEXT"),
            ("ack_recipients", "recipient_name", "TEXT"),
            ("ack_recipients", "sent_at", "TEXT"),
            ("ack_recipients", "confirmed_at", "TEXT"),
            ("ack_recipients", "updated_at", "TEXT"),
            ("reminder_log", "recipient_email", "TEXT"),
            ("reminder_log", "error", "TEXT"),
        ]:
            _add_column_if_missing(conn, table, column, definition)

        # 状态规范化
        conn.execute("UPDATE notifications SET issuer = department WHERE (issuer IS NULL OR issuer = '') AND department IS NOT NULL")
        conn.execute("UPDATE notifications SET owner = drafter WHERE (owner IS NULL OR owner = '') AND drafter IS NOT NULL")
        conn.execute("UPDATE notifications SET description = purpose WHERE (description IS NULL OR description = '') AND purpose IS NOT NULL")
        conn.execute("UPDATE notifications SET impact_role = target_scope WHERE (impact_role IS NULL OR impact_role = '') AND target_scope IS NOT NULL")
        conn.execute("UPDATE notifications SET deadline = effective_end WHERE (deadline IS NULL OR deadline = '') AND effective_end IS NOT NULL")
        conn.execute("UPDATE notifications SET status = '草稿' WHERE status IN ('Draft', '草稿', '待审批', '待发布')")
        conn.execute("UPDATE notifications SET status = '执行中' WHERE status IN ('Sent', '已发送', '执行中', '已发布')")
        conn.execute("UPDATE notifications SET status = '已回执' WHERE status IN ('Acknowledged', '已回执')")
        conn.execute("UPDATE notifications SET status = '已完成' WHERE status IN ('Completed', '已完成', '已归档')")
        conn.execute("UPDATE notifications SET status = '已逾期' WHERE status IN ('Overdue', '已截止', '已过期')")
        conn.execute("UPDATE plans SET status = '已编写' WHERE status IN ('待发布', '未开始', '制定中')")
        conn.execute(
            "UPDATE notifications SET status = '已逾期'"
            " WHERE status IN ('执行中', '已回执') AND COALESCE(deadline, effective_end) IS NOT NULL AND COALESCE(deadline, effective_end) < ?",
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


def log_action(notification_id: str, action: str, detail: str = "", actor: str = "系统") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (notification_id, action, detail, actor, timestamp) VALUES (?, ?, ?, ?, ?)",
            (notification_id, action, detail, actor, datetime.now().isoformat()),
        )
