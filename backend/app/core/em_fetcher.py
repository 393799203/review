#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富 F10 核心题材接口：个股 → 所属板块列表（带相关度排名）

接口：https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code=SZ300413
返回 ssbk[]：{BOARD_CODE, BOARD_NAME, BOARD_RANK, ...}

- 并发批量请求（线程池）
- 进程级缓存（按日期，code -> [(board_name, rank), ...]）
- 失败返回 None，调用方回退其他匹配
"""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Dict, List, Optional, Tuple

import requests

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      'Chrome/151.0.0.0 Safari/537.36')

# 进程级缓存：code -> [(board_name, rank), ...]
_cache: Dict[str, List[Tuple[str, int]]] = {}
_cache_date: str = ''
_lock = threading.Lock()


def _to_em_code(code: str) -> str:
    """6 位代码 → 东财 F10 code（SZ/SH 前缀）"""
    code = str(code).strip()
    prefix = 'SZ' if code.startswith(('0', '3')) else 'SH'
    return f'{prefix}{code}'


def _fetch_one(code: str) -> Optional[List[Tuple[str, int]]]:
    """请求单只股票板块列表"""
    url = f'https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax?code={_to_em_code(code)}'
    try:
        resp = requests.get(url, headers={'User-Agent': UA, 'Referer': 'https://emweb.securities.eastmoney.com/'}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        ssbk = data.get('ssbk') or []
        boards = []
        for b in ssbk:
            name = (b.get('BOARD_NAME') or '').strip()
            rank = int(b.get('BOARD_RANK') or 0)
            if name:
                boards.append((name, rank))
        return boards or None
    except Exception as e:
        print(f'⚠️ 东财板块接口失败 {code}: {e}')
        return None


def get_stock_boards_batch(codes: List[str], force: bool = False) -> Dict[str, List[Tuple[str, int]]]:
    """
    批量获取个股板块列表（并发 + 缓存）

    Returns:
        {code: [(board_name, rank), ...]}；失败的股票不在返回中
    """
    global _cache_date
    today = date.today().isoformat()

    codes = [str(c).strip() for c in codes if str(c).strip()]
    if not codes:
        return {}

    with _lock:
        if _cache_date != today:
            _cache.clear()
            _cache_date = today
        missing = [c for c in codes if c not in _cache]

    result = {}
    with _lock:
        for c in codes:
            if c in _cache:
                result[c] = _cache[c]

    if missing:
        fetched = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_one, c): c for c in missing}
            for fut in futures:
                c = futures[fut]
                try:
                    boards = fut.result()
                    if boards:
                        fetched[c] = boards
                except Exception:
                    pass
        with _lock:
            for c, boards in fetched.items():
                _cache[c] = boards
                result[c] = boards
    return result
