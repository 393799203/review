#!/usr/bin/env python3
r"""
基本面财务快照同步：从通达信行情主站（mootdx get_finance_info）拉取全市场财务数据，
写入 tdx.raw_stock_finance。每次全量快照，按 (symbol, updated_date) upsert，
自然积累多期历史（几期后可算同比增速等成长因子）。

字段来源：通达信 get_finance_info 的 37 字段（股本/资产/营收/利润/现金流/负债/每股净资产等）。

用法:
  python sync_fundamental_standalone.py                    # 全市场（默认）
  python sync_fundamental_standalone.py --limit 200        # 只处理前 200 个（测试）
  python sync_fundamental_standalone.py --threads 8        # 8 线程（默认）

说明:
  - 只同步沪深A股（00/30/60/68，北交所 get_finance_info 不支持）
  - 每次运行约 5000 只 × 0.3s / 线程数 ≈ 3~8 分钟（建议每周后台跑一次）
  - 依赖 mootdx（tdx-daily 镜像已含）；TDX 行情主站自动选取
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Any, Optional

from tdx_config import get_db_url

DEFAULT_DB_URL = get_db_url()

# get_finance_info 的全部字段（列顺序即插入顺序）
FINANCE_FIELDS = [
    "market", "code", "liutongguben", "province", "industry", "updated_date",
    "ipo_date", "zongguben", "guojiagu", "faqirenfarengu", "farengu", "bgu",
    "hgu", "zhigonggu", "zongzichan", "liudongzichan", "gudingzichan",
    "wuxingzichan", "gudongrenshu", "liudongfuzhai", "changqifuzhai",
    "zibengongjijin", "jingzichan", "zhuyingshouru", "zhuyinglirun",
    "yingshouzhangkuan", "yingyelirun", "touzishouyu", "jingyingxianjinliu",
    "zongxianjinliu", "cunhuo", "lirunzonghe", "shuihoulirun", "jinglirun",
    "weifenpeilirun", "meigujingzichan", "baoliu2",
]

# 每线程一个 mootdx 连接（thread-local）
_local = threading.local()

# 备用行情主站（mootdx 无配置时写入；180.153.18.170 为已验证可用的 BESTIP）
FALLBACK_SERVERS = [
    ["备用A", "180.153.18.170", 7709],
    ["备用B", "124.71.187.122", 7709],
    ["备用C", "110.41.147.114", 7709],
]


# 配置写入锁（防多线程并发写坏配置文件）
_config_lock = threading.Lock()


def _ensure_mootdx_config() -> None:
    """mootdx 无 config.json 时写入最小可用配置（BESTIP 指向已验证主站）。
    原子写入（临时文件 + os.replace），线程安全；应在线程池启动前调用一次。"""
    import json
    import os

    cfg_dir = os.path.expanduser("~/.mootdx")
    cfg_file = os.path.join(cfg_dir, "config.json")
    if os.path.exists(cfg_file):
        return
    with _config_lock:
        if os.path.exists(cfg_file):
            return
        os.makedirs(cfg_dir, exist_ok=True)
        tmp = cfg_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "SERVER": {"HQ": FALLBACK_SERVERS, "EX": [], "GP": []},
                    "BESTIP": {"HQ": ["180.153.18.170", 7709], "EX": "", "GP": ""},
                    "TDXDIR": ":",
                },
                f,
            )
        os.replace(tmp, cfg_file)


def _client():
    from mootdx.quotes import Quotes

    if getattr(_local, "client", None) is None:
        _ensure_mootdx_config()
        _local.client = Quotes.factory(market="std", bestip=False)
    return _local.client


def symbol_to_market_code(symbol: str) -> tuple[int, str]:
    """tdx symbol → (mootdx market, 6位code)；北交所返回 None"""
    if symbol.startswith(("sh60", "sh68")):
        return 1, symbol[2:]
    if symbol.startswith(("sz00", "sz30")):
        return 0, symbol[2:]
    return -1, ""


def fetch_one(symbol: str) -> Optional[dict]:
    """拉取单只财务快照；失败返回 None"""
    market, code = symbol_to_market_code(symbol)
    if market < 0:
        return None
    try:
        api = _client().client
        info = api.get_finance_info(market, code)
        if not info:
            return None
        info["symbol"] = symbol
        return info
    except Exception:
        return None


# 显式声明的元数据列（不在动态 DOUBLE PRECISION 列中重复）
EXPLICIT_COLS = {"market", "code", "updated_date", "ipo_date"}
DYNAMIC_COLS = [f for f in FINANCE_FIELDS if f not in EXPLICIT_COLS]


def ensure_table(conn) -> None:
    cols = ", ".join(f'"{f}" DOUBLE PRECISION' for f in DYNAMIC_COLS)
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS tdx.raw_stock_finance (
                symbol TEXT NOT NULL,
                updated_date INT,
                ipo_date DOUBLE PRECISION,
                market DOUBLE PRECISION,
                code TEXT,
                {cols},
                fetch_date DATE NOT NULL DEFAULT CURRENT_DATE,
                UNIQUE (symbol, updated_date)
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_raw_stock_finance_symbol "
            "ON tdx.raw_stock_finance (symbol);"
        )
    conn.commit()


def get_symbols(conn, limit: int) -> list[str]:
    sql = """
        SELECT DISTINCT substr(symbol, 1, 2) AS mk, symbol
        FROM tdx.raw_stocks_daily
        WHERE (symbol LIKE 'sh60%' OR symbol LIKE 'sh68%'
               OR symbol LIKE 'sz00%' OR symbol LIKE 'sz30%')
        ORDER BY symbol
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        syms = [r[1] for r in cur.fetchall()]
    return syms[:limit] if limit > 0 else syms


def _clean(v):
    """清洗字段值：去 NUL/控制字符；数字字符串转 float；无法转的置 None"""
    if v is None:
        return None
    if isinstance(v, str):
        v2 = "".join(ch for ch in v if ch >= " " and ch != "\x00").strip()
        if not v2:
            return None
        try:
            return float(v2)
        except ValueError:
            return None
    return v


def insert_snapshots(conn, rows: list[dict], batch: int = 2000) -> int:
    from psycopg2.extras import execute_values

    if not rows:
        return 0
    tuples = []
    for r in rows:
        sym = str(r["symbol"]).strip()
        upd = _clean(r.get("updated_date"))
        ipo = _clean(r.get("ipo_date"))
        mk = _clean(r.get("market"))
        code = _clean(r.get("code"))
        vals = tuple(_clean(r.get(f)) for f in DYNAMIC_COLS)
        tuples.append((sym, upd, ipo, mk, code) + vals + (date.today(),))
    names = ", ".join(f'"{f}"' for f in DYNAMIC_COLS)
    total = 0
    for i in range(0, len(tuples), batch):
        chunk = tuples[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO tdx.raw_stock_finance
                (symbol, updated_date, ipo_date, market, code, {names}, fetch_date)
                VALUES %s
                ON CONFLICT (symbol, updated_date) DO UPDATE SET
                    {", ".join(f'"{f}" = EXCLUDED."{f}"' for f in DYNAMIC_COLS)},
                    ipo_date = EXCLUDED.ipo_date, market = EXCLUDED.market,
                    code = EXCLUDED.code, fetch_date = EXCLUDED.fetch_date
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="通达信财务快照同步 → tdx.raw_stock_finance")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL)
    parser.add_argument("--limit", type=int, default=0, metavar="N", help="只处理前 N 个标的（0=全部）")
    parser.add_argument("--threads", type=int, default=8, help="并发连接数（默认 8）")
    args = parser.parse_args()

    import psycopg2

    _ensure_mootdx_config()  # 主线程先建立配置（线程池并发写配置文件会写坏）
    conn = psycopg2.connect(args.db_url)
    try:
        ensure_table(conn)
        symbols = get_symbols(conn, args.limit)
        print(f"待同步 {len(symbols):,} 只标的（{args.threads} 线程）…")

        results: list[dict] = []
        t0 = time.time()
        done = 0
        ok = 0
        with ThreadPoolExecutor(max_workers=args.threads) as ex:
            futures = {ex.submit(fetch_one, s): s for s in symbols}
            for fut in as_completed(futures):
                info = fut.result()
                done += 1
                if info:
                    results.append(info)
                    ok += 1
                if done % 500 == 0:
                    print(f"  … {done:,}/{len(symbols):,}（成功 {ok:,}）", flush=True)
        print(f"拉取完成: {ok:,}/{len(symbols):,} 成功，耗时 {time.time()-t0:.0f}s")

        if results:
            n = insert_snapshots(conn, results)
            print(f"已写入 tdx.raw_stock_finance: {n:,} 行（含更新）")
    finally:
        conn.close()


if __name__ == "__main__":
    main()