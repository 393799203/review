"""
TDX_daily 独立包配置：仅从本目录 .env 与环境变量读取 DB_URL，不依赖上级 DataSource/config。
"""
from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    env_path = PACKAGE_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

# 默认连接串仅作占位；生产请务必配置 .env 或环境变量 DB_URL
_DEFAULT_DB = "postgresql://postgres:postgres@localhost:5432/quantdb"


def get_db_url() -> str:
    return os.environ.get("DB_URL", "").strip() or _DEFAULT_DB
