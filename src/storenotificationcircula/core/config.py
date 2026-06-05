from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def secret(key: str, default: str = "") -> str:
    return os.getenv(key, default)
