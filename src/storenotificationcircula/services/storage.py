from __future__ import annotations

import os
from pathlib import Path

from supabase import Client, create_client

BUCKET = "notifications"


def _secret(key: str, default: str = "") -> str:
    value = os.environ.get(key, default)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default


def _storage_mode() -> str:
    return _secret("APP_STORAGE_MODE", "local").strip().lower()


def _local_dir() -> Path:
    raw_path = _secret("LOCAL_UPLOAD_DIR", "data/uploads")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _local_path(storage_key: str) -> Path:
    return _local_dir() / Path(storage_key).name


def _client() -> Client:
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY 未配置。")
    return create_client(url, key)


def upload_file(storage_key: str, data: bytes) -> None:
    """保存 PDF。默认写入本地目录；配置 APP_STORAGE_MODE=supabase 后上传云存储。"""
    if _storage_mode() != "supabase":
        _local_path(storage_key).write_bytes(data)
        return
    _client().storage.from_(BUCKET).upload(storage_key, data)


def download_file(storage_key: str) -> bytes:
    """读取 PDF 原始字节。"""
    if _storage_mode() != "supabase":
        return _local_path(storage_key).read_bytes()
    return _client().storage.from_(BUCKET).download(storage_key)


def delete_file(storage_key: str) -> None:
    """删除 PDF。"""
    if _storage_mode() != "supabase":
        _local_path(storage_key).unlink(missing_ok=True)
        return
    _client().storage.from_(BUCKET).remove([storage_key])


def original_filename(storage_key: str) -> str:
    """从 storage_key（格式：{uuid}_{原始文件名}）中还原原始文件名。"""
    parts = storage_key.split("_", 1)
    return parts[1] if len(parts) == 2 else storage_key
