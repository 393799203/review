#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺板块 + 成分股全量同步脚本

拉取：
  1. THS 全量板块目录（概念 390 + 行业 320）→ upsert 到 stock_review.dim_block
  2. 全板块成分股 → 重建 quantdb.tdx.dim_stock_block（股票×板块关系表）
  3. 聚合每股概念/行业 → 重建 quantdb.tdx.dim_stock_info（每股一行：concepts/industries，含名称）

用法（服务器，.env 需含 THS_API_KEY / DATABASE_URL / TDX_DATABASE_URL）：
  docker compose exec -T backend python scripts/sync_ths_boards.py

依赖：requests、psycopg2-binary（requirements.txt 已有）
"""

import json
import os
import sys
import time

import psycopg2
import requests

API_KEY = os.environ.get('THS_API_KEY', '')
BASE = 'https://fuyao.aicubes.cn/api/a-share-index'
HEADERS = {'X-api-key': API_KEY}

# 板块代码统一为 6 位数字（去掉 .TI 后缀）
def clean_plate_code(thscode: str) -> str:
    return thscode.replace('.TI', '')


def get_json(path: str, params: dict, retries: int = 4) -> dict:
    url = f'{BASE}{path}'
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get('code') != 0:
                raise RuntimeError(f"code={data.get('code')} {data.get('message')}")
            return data
        except Exception as e:
            last = e
            print(f'  ⚠️ 第{i+1}次失败 {path} {params}: {e}', flush=True)
            time.sleep(1.0 * (i + 1))
    raise last


def fetch_catalog() -> list:
    """返回 [(plate_code, name, board_type), ...]"""
    boards = []
    for tag, btype in (('cn_concept', 'concept'), ('industry', 'industry')):
        data = get_json('/catalog/ths-index-list', {'tag': tag})
        items = data['data']['item']
        for it in items:
            boards.append((clean_plate_code(it['thscode']), it['name'], btype))
        print(f'  目录 {btype}: {len(items)} 个', flush=True)
    return boards


def fetch_components(boards: list) -> list:
    """返回 [(plate_code, symbol, stock_name), ...]（symbol 已转 tdx 格式，已过滤非 A 股）"""
    def to_symbol(ticker: str, thscode: str):
        suffix = (thscode or '').split('.')[-1].upper()
        pre = {'SZ': 'sz', 'SH': 'sh', 'BJ': 'bj'}.get(suffix)
        if not pre:
            return None
        return f'{pre}{ticker}'

    def is_a_stock(symbol: str) -> bool:
        if not symbol:
            return False
        code6 = symbol[2:]
        if len(code6) != 6 or not code6.isdigit():
            return False
        if symbol.startswith('sh'):
            return code6.startswith(('60', '68'))
        if symbol.startswith('sz'):
            return code6.startswith(('00', '30'))
        if symbol.startswith('bj'):
            return True
        return False

    rows, fails = [], []
    for i, (plate, name, _btype) in enumerate(boards):
        try:
            data = get_json('/constituents/ths-stock-list', {'thscode': f'{plate}.TI'})
        except Exception as e:
            fails.append((plate, str(e)))
            print(f'  ❌ {plate} {name}: {e}', flush=True)
            continue
        for it in data.get('data', {}).get('item', []):
            sym = to_symbol(it.get('ticker', ''), it.get('thscode', ''))
            if sym and is_a_stock(sym):
                rows.append((plate, sym, it.get('name', '')))
        if (i + 1) % 50 == 0:
            print(f'  进度 {i+1}/{len(boards)}, 累计成分 {len(rows)}', flush=True)
        time.sleep(0.12)
    print(f'  成分合计: {len(rows)}, 失败板块: {len(fails)}', flush=True)
    for f in fails[:10]:
        print('    失败:', f)
    return rows


def sync_dim_block(conn, boards: list):
    """upsert 全量板块目录到 dim_block（保留 THS 目录之外的 block_top 旧板块）"""
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
    cur.execute("CREATE TEMP TABLE tmp_ths_boards (plate_code TEXT PRIMARY KEY, plate_name TEXT, board_type TEXT) ON COMMIT DROP")
    for plate, name, btype in boards:
        cur.execute("INSERT INTO tmp_ths_boards VALUES (%s,%s,%s)", (plate, name, btype))
    cur.execute("""
        INSERT INTO dim_block (plate_code, plate_name, board_type, change_pct, updated_at)
        SELECT plate_code, plate_name, board_type, NULL, now() FROM tmp_ths_boards
        ON CONFLICT (plate_code) DO UPDATE SET
            plate_name = EXCLUDED.plate_name,
            board_type = EXCLUDED.board_type,
            updated_at = now()
    """)
    conn.commit()
    cur.execute("SELECT board_type, COUNT(*) FROM dim_block GROUP BY 1 ORDER BY 1")
    print('  dim_block 类型分布:', cur.fetchall(), flush=True)


def sync_quantdb(conn, components: list, boards_by_code: dict):
    """重建 dim_stock_block（关系）与 dim_stock_info（每股聚合）"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tdx.dim_stock_block (
            symbol TEXT NOT NULL,
            plate_code TEXT NOT NULL,
            stock_name TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (symbol, plate_code)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dim_stock_block_plate ON tdx.dim_stock_block (plate_code)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tdx.dim_stock_info (
            symbol TEXT PRIMARY KEY,
            stock_code TEXT,
            stock_name TEXT,
            market TEXT,
            concept_codes JSONB,
            industry_codes JSONB,
            concept_names JSONB,
            industry_names JSONB,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # 1. 关系表全量重建
    cur.execute("TRUNCATE tdx.dim_stock_block")
    from psycopg2.extras import execute_values
    execute_values(cur,
        "INSERT INTO tdx.dim_stock_block (symbol, plate_code, stock_name) VALUES %s",
        [(sym, plate, nm) for plate, sym, nm in components], page_size=5000)
    print(f'  dim_stock_block: {len(components)} 条', flush=True)

    # 2. 每股聚合
    agg = {}
    for plate, sym, nm in components:
        a = agg.setdefault(sym, {'names': set(), 'c': set(), 'i': set()})
        a['names'].add(nm)
        btype, bname = boards_by_code.get(plate, ('?', ''))
        if btype == 'concept':
            a['c'].add(plate)
        elif btype == 'industry':
            a['i'].add(plate)
    infos = []
    for sym, a in agg.items():
        name = max(a['names'], key=len) if a['names'] else ''
        cc, ic = sorted(a['c']), sorted(a['i'])
        cnames = sorted({boards_by_code.get(c, ('', ''))[1] for c in cc if boards_by_code.get(c, ('', ''))[1]})
        inames = sorted({boards_by_code.get(i, ('', ''))[1] for i in ic if boards_by_code.get(i, ('', ''))[1]})
        infos.append((sym, sym[2:], name, sym[:2],
                      json.dumps(cc, ensure_ascii=False), json.dumps(ic, ensure_ascii=False),
                      json.dumps(cnames, ensure_ascii=False), json.dumps(inames, ensure_ascii=False)))
    cur.execute("TRUNCATE tdx.dim_stock_info")
    execute_values(cur, """
        INSERT INTO tdx.dim_stock_info
            (symbol, stock_code, stock_name, market, concept_codes, industry_codes, concept_names, industry_names)
        VALUES %s
    """, infos, page_size=5000)
    print(f'  dim_stock_info: {len(infos)} 只', flush=True)
    conn.commit()


def main() -> int:
    if not API_KEY:
        print('缺少 THS_API_KEY 环境变量')
        return 1
    print('① 拉取板块目录...')
    boards = fetch_catalog()
    print(f'  板块合计: {len(boards)}')
    boards_by_code = {p: (t, n) for p, n, t in boards}

    print('② 拉取成分股...')
    components = fetch_components(boards)

    print('③ 同步 stock_review.dim_block ...')
    conn1 = psycopg2.connect(os.environ.get('DATABASE_URL', ''))
    try:
        sync_dim_block(conn1, boards)
    finally:
        conn1.close()

    print('④ 同步 quantdb tdx.* ...')
    conn2 = psycopg2.connect(os.environ.get('TDX_DATABASE_URL', ''))
    try:
        sync_quantdb(conn2, components, boards_by_code)
    finally:
        conn2.close()

    print('✅ 同步完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())