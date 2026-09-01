#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量板块维表构建：dim_block

数据源：
1. 同花顺概念板块全量（q.10jqka.com.cn/gn/，约 292 个，含当日涨跌幅）
2. blocks 表历史板块（block_top 返回的强势板块，补全新板块如"人工智能"）

用法（服务器）：
  docker compose exec -T backend python scripts/fetch_dim_blocks.py
"""

import json
import os
import re
import sys
import urllib.request
import gzip

import psycopg2

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      'Chrome/151.0.0.0 Safari/537.36')


def fetch(url: str, referer: str = 'http://q.10jqka.com.cn/gn/') -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': referer,
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.decompress(raw)
    return raw.decode('gbk', errors='ignore')


def parse_concept_boards(html: str) -> dict:
    """解析 q.10jqka.com.cn/gn/ 内嵌 gnSection JSON"""
    m = re.search(r'id="gnSection" value=\'(.*?)\'\s*>', html, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
        return {
            it['platecode']: {
                'name': it.get('platename', ''),
                'change_pct': it.get('199112'),
            }
            for it in data.values() if it.get('platecode') and it.get('platename')
        }
    except Exception:
        return {}


def main() -> int:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', ''))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dim_block (
            plate_code TEXT PRIMARY KEY,
            plate_name TEXT NOT NULL,
            board_type TEXT NOT NULL DEFAULT 'concept',
            change_pct DOUBLE PRECISION,
            updated_at TIMESTAMP DEFAULT now()
        )
    """)
    conn.commit()

    boards = {}  # code -> dict

    # 1. 概念板块（多页抓取，去重；page 不稳定但第一页已覆盖主流）
    for p in range(1, 4):
        url = f'http://q.10jqka.com.cn/gn/index/field/199112/order/desc/page/{p}/'
        try:
            page_boards = parse_concept_boards(fetch(url))
        except Exception as e:
            print(f'概念板块 page{p} 抓取失败: {e}')
            break
        if not page_boards:
            break
        new = sum(1 for k in page_boards if k not in boards)
        for code, info in page_boards.items():
            if code not in boards:
                boards[code] = {**info, 'type': 'concept'}
        print(f'概念板块 page{p}: {len(page_boards)} 个, 新增 {new}')
        if new == 0:
            break

    print(f'概念板块合计: {len(boards)} 个')

    # 2. blocks 历史板块补充（含 block_top 的新板块如"人工智能"）
    cur.execute("SELECT DISTINCT block_code, block_name FROM blocks")
    for block_code, block_name in cur.fetchall():
        code = str(block_code).strip()
        name = str(block_name).strip()
        if not code or not name:
            continue
        if code not in boards:
            boards[code] = {'name': name, 'change_pct': None, 'type': 'block_top'}
        elif name != boards[code]['name']:
            # block_top 名称优先（与当天统计对齐）
            boards[code]['name'] = name

    # 写入
    total = 0
    for code, info in boards.items():
        cur.execute("""
            INSERT INTO dim_block (plate_code, plate_name, board_type, change_pct, updated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (plate_code) DO UPDATE SET
                plate_name = EXCLUDED.plate_name,
                change_pct = EXCLUDED.change_pct,
                updated_at = now()
        """, (code, info['name'], info['type'], info['change_pct']))
        total += 1
    conn.commit()
    print(f'已写入 dim_block: {total} 个板块')

    # 验证
    cur.execute("""
        SELECT COUNT(*), COUNT(*) FILTER (WHERE board_type='concept'),
               COUNT(*) FILTER (WHERE board_type='block_top')
        FROM dim_block
    """)
    n, n_concept, n_top = cur.fetchone()
    print(f'验证: 共 {n} | 概念 {n_concept} | block_top 补充 {n_top}')

    cur.execute("SELECT plate_name FROM dim_block WHERE plate_name LIKE '%人工智能%' LIMIT 3")
    ai = [r[0] for r in cur.fetchall()]
    print(f'含"人工智能": {ai}')

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
