#!/usr/bin/env python3
r"""
指数成分股同步：从东财板块接口拉取指数成分，写入 tdx.dim_index_member。

东财板块代码（fs=b:BKxxxx）：
  BK0500 = 沪深300（已验证 300 只）

用法:
  python sync_index_constituents.py                 # 同步全部已配置指数
  python sync_index_constituents.py --index hs300   # 只同步指定指数
  python sync_index_constituents.py --dry-run       # 只打印不写库

说明:
  - 代码转 tdx 格式（sh/sz 前缀），与 tdx.raw_stock_indicators.symbol 一致
  - 成分股按当前成分（指数成分定期调整，历史回测用现成分近似，使用时注意）
  - 新增指数：在 INDEXES 字典加一行 (东财板块码, 中文名) 即可
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/151.0 Safari/537.36"

# index 值 -> (东财板块码, 中文名)；universe 值直接用 index 值
INDEXES: dict[str, tuple[str, str]] = {
    "hs300": ("BK0500", "沪深300"),
    # 需要更多指数时在此追加，例如： "zz500": ("BK0501", "中证500"),
}

CLIST_URL = ("https://push2.eastmoney.com/api/qt/clist/get"
             "?pn={page}&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=b:{bk}&fields=f12,f14")


def _to_tdx_symbol(code6: str) -> str | None:
    if code6.startswith(("60", "68", "51", "58")):
        return f"sh{code6}"
    if code6.startswith(("00", "30", "12", "15")):
        return f"sz{code6}"
    return None  # 北交所等不在沪深300内


def fetch_index(index: str) -> list[tuple[str, str]]:
    bk, _cn = INDEXES[index]
    out: list[tuple[str, str]] = []
    page = 1
    total = None
    while True:
        url = CLIST_URL.format(page=page, bk=bk)
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=20) as resp:
            data = json.load(resp).get("data") or {}
        if total is None:
            total = data.get("total") or 0
        diff = data.get("diff") or []
        if not diff:
            break
        for x in diff:
            sym = _to_tdx_symbol(str(x.get("f12", "")))
            if sym:
                out.append((sym, str(x.get("f14", ""))))
        if len(out) >= total or len(diff) < 100:
            break
        page += 1
    return out


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.dim_index_member (
                "index" TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE ("index", symbol)
            );
            """
        )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="指数成分同步 → tdx.dim_index_member")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--index", type=str, default=None, help="只同步指定指数（缺省全部）")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写库")
    args = parser.parse_args()

    indexes = [args.index] if args.index else list(INDEXES)
    unknown = [i for i in indexes if i not in INDEXES]
    if unknown:
        print(f"未知指数: {unknown}，可选: {list(INDEXES)}", file=sys.stderr)
        sys.exit(1)

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        if not args.dry_run:
            ensure_table(conn)
        for idx in indexes:
            rows = fetch_index(idx)
            cn = INDEXES[idx][1]
            print(f"{idx}({cn}): 拉到 {len(rows)} 只成分")
            if not rows:
                print(f"  警告: {idx} 无数据，请检查东财板块码", file=sys.stderr)
                continue
            if args.dry_run:
                for sym, name in rows[:5]:
                    print(f"  {sym} {name}")
                continue
            with conn.cursor() as cur:
                cur.execute('DELETE FROM tdx.dim_index_member WHERE "index" = %s', (idx,))
            conn.commit()
            from psycopg2.extras import execute_values

            tuples = [(idx, sym, name) for sym, name in rows]
            for i in range(0, len(tuples), 2000):
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO tdx.dim_index_member ("index", symbol, name)
                        VALUES %s
                        ON CONFLICT ("index", symbol) DO UPDATE SET name = EXCLUDED.name,
                            updated_at = now()
                        """,
                        tuples[i : i + 2000],
                    )
                conn.commit()
            print(f"  已写入 tdx.dim_index_member: {idx} {len(rows)} 只")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
