from __future__ import annotations

import os

from supabase import Client, create_client

BUCKET = "notifications"


def _client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL", "")
            key = key or st.secrets.get("SUPABASE_KEY", "")
        except Exception:
            pass
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY 未配置。")
    return create_client(url, key)


def upload_file(storage_key: str, data: bytes) -> None:
    """上传文件到 Supabase Storage。storage_key 作为存储路径。"""
    _client().storage.from_(BUCKET).upload(storage_key, data)


def download_file(storage_key: str) -> bytes:
    """从 Supabase Storage 下载文件，返回原始字节。"""
    return _client().storage.from_(BUCKET).download(storage_key)


def delete_file(storage_key: str) -> None:
    """从 Supabase Storage 删除文件。"""
    _client().storage.from_(BUCKET).remove([storage_key])


def original_filename(storage_key: str) -> str:
    """从 storage_key（格式：{uuid}_{原始文件名}）中还原原始文件名。"""
    parts = storage_key.split("_", 1)
    return parts[1] if len(parts) == 2 else storage_key
