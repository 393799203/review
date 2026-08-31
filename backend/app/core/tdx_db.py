#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDX 外部行情库连接（PostgreSQL，schema=tdx，只读）

通过环境变量 TDX_DATABASE_URL 配置，例如：
    TDX_DATABASE_URL=postgresql://user:pass@host:5432/quantdb

未配置时 get_tdx_engine() 返回 None，相关接口应返回 503。
"""

import os
from sqlalchemy import create_engine

_engine = None


class TdxNotConfiguredError(Exception):
    """TDX 行情库未配置"""
    pass


def get_tdx_engine():
    """
    获取 TDX 行情库 engine（懒加载单例，小连接池，只读用途）

    Returns:
        Engine 或 None（未配置 TDX_DATABASE_URL 时）
    """
    global _engine
    url = os.getenv('TDX_DATABASE_URL')
    if not url:
        return None
    if _engine is None:
        _engine = create_engine(
            url,
            echo=False,
            pool_size=3,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def require_tdx_engine():
    """
    获取 TDX engine，未配置时抛出 TdxNotConfiguredError
    """
    engine = get_tdx_engine()
    if engine is None:
        raise TdxNotConfiguredError(
            'TDX 行情库未配置，请在 review/.env 中添加 '
            'TDX_DATABASE_URL=postgresql://user:pass@host:5432/quantdb'
        )
    return engine
