#!/usr/bin/env python3
r"""
复现 tdx2db 的 update_gbbq：下载 gbbq.zip → 解压 → 按 Go 版逻辑解密解析 → 写入 PostgreSQL tdx.raw_gbbq。

逻辑对齐：
  - tdx2db/workflow/tasks.go: getGbbqFile
  - tdx2db/tdx/gbbq.go: DecodeGbbqFile, decryptBlockToBuf, fastParseDate
  - tdx2db/utils/symbol.go: GenerateSymbol
  - tdx2db/database/postgresql/dml.go: ImportGBBQ（先 TRUNCATE 再导入）

依赖: pip install psycopg2-binary（仅写库时需要；下载使用标准库 urllib）

用法:
  python import_gbbq_standalone.py
  python import_gbbq_standalone.py --db-url "postgresql://..."
  python import_gbbq_standalone.py --dry-run   # 只下载解析，不写库
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from urllib.request import urlopen

from tdx_config import PACKAGE_ROOT, get_db_url

DEFAULT_DB_URL = get_db_url()

GBBQ_URL = "http://www.tdx.com.cn/products/data/data/dbf/gbbq.zip"
HEX_KEYS_FILE = PACKAGE_ROOT / "data" / "gbbq_hex_keys.txt"


def load_keys() -> bytes:
    """密钥取自打包文件 data/gbbq_hex_keys.txt（与原版 gbbq_var.go HexKeys 一致），无需 Go 源码。"""
    if not HEX_KEYS_FILE.is_file():
        raise RuntimeError(f"缺少 GBBQ 密钥文件: {HEX_KEYS_FILE}")
    text = HEX_KEYS_FILE.read_text(encoding="utf-8").strip()
    return bytes.fromhex(text.replace(" ", ""))


def _u32(x: int) -> int:
    """Go uint32 语义。"""
    return x & 0xFFFFFFFF


def decrypt_block_to_buf(keys: memoryview, encrypted: bytes, dst: bytearray) -> None:
    """与 tdx2db/tdx/gbbq.go decryptBlockToBuf 一致（uint32 回绕）。"""
    eax = struct.unpack_from("<I", keys, 0x44)[0]
    A = struct.unpack_from("<I", encrypted, 0)[0]
    B = struct.unpack_from("<I", encrypted, 4)[0]
    num = _u32(eax ^ A)
    numold = _u32(B)
    j = 0x40
    while j >= 4:
        ebx = (num & 0xFF0000) >> 16
        offset = ebx * 4 + 0x448
        eax = struct.unpack_from("<I", keys, offset)[0]

        ebx = num >> 24
        offset = ebx * 4 + 0x48
        eax = _u32(eax + struct.unpack_from("<I", keys, offset)[0])

        ebx = (num & 0xFF00) >> 8
        offset = ebx * 4 + 0x848
        eax = _u32(eax ^ struct.unpack_from("<I", keys, offset)[0])

        ebx = num & 0xFF
        offset = ebx * 4 + 0xC48
        eax = _u32(eax + struct.unpack_from("<I", keys, offset)[0])

        eax = _u32(eax ^ struct.unpack_from("<I", keys, j)[0])

        temp = num
        num = _u32(numold ^ eax)
        numold = temp
        j -= 4

    numold = _u32(numold ^ struct.unpack_from("<I", keys, 0)[0])
    struct.pack_into("<I", dst, 0, numold)
    struct.pack_into("<I", dst, 4, num)


def fast_parse_date(d: int) -> date | None:
    if d == 0:
        return None
    y = d // 10000
    m = (d % 10000) // 100
    day = d % 100
    if m < 1 or m > 12 or day < 1 or day > 31:
        return None
    try:
        return date(y, m, day)
    except ValueError:
        return None


def generate_symbol(code: str) -> tuple[str, bool]:
    """与 tdx2db/utils/symbol.go GenerateSymbol 一致。"""
    if len(code) < 2:
        return code, False
    prefix = code[:2]
    if prefix in ("00", "30"):
        return "sz" + code, True
    if prefix in ("60", "68"):
        return "sh" + code, True
    if prefix in ("92", "87", "83", "43"):
        return "bj" + code, True
    return code, False


def decode_gbbq_file(path: Path, keys: bytes) -> list[tuple[int, str, date, float, float, float, float]]:
    """与 tdx2db/tdx/gbbq.go DecodeGbbqFile 一致，返回行元组列表。"""
    content = path.read_bytes()
    if len(content) < 4:
        return []

    count = struct.unpack_from("<I", content, 0)[0]
    mv = memoryview(keys)
    clear = bytearray(29)
    pos = 4
    total = len(content)
    rows: list[tuple[int, str, date, float, float, float, float]] = []

    blk = bytearray(8)
    for _ in range(count):
        if pos + 29 > total:
            break

        # 注意：不能对 clear[8:16] 切片调用 pack_into，bytearray 切片是副本，与 Go 的 clearData[8:16] 视图不同
        decrypt_block_to_buf(mv, content[pos : pos + 8], blk)
        clear[0:8] = blk
        pos += 8
        decrypt_block_to_buf(mv, content[pos : pos + 8], blk)
        clear[8:16] = blk
        pos += 8
        decrypt_block_to_buf(mv, content[pos : pos + 8], blk)
        clear[16:24] = blk
        pos += 8
        clear[24:29] = content[pos : pos + 5]
        pos += 5

        code_bytes = clear[1:8]
        nul = code_bytes.find(b"\x00")
        if nul >= 0:
            code_bytes = code_bytes[:nul]
        code = code_bytes.decode("ascii", errors="ignore")
        symbol, ok = generate_symbol(code)
        if not ok:
            continue

        date_int = struct.unpack_from("<I", clear, 8)[0]
        dt = fast_parse_date(date_int)
        if dt is None:
            continue

        category = clear[12]
        c1 = struct.unpack_from("<f", clear, 13)[0]
        c2 = struct.unpack_from("<f", clear, 17)[0]
        c3 = struct.unpack_from("<f", clear, 21)[0]
        c4 = struct.unpack_from("<f", clear, 25)[0]

        if math.isnan(c1):
            c1 = 0.0
        if math.isnan(c2):
            c2 = 0.0
        if math.isnan(c3):
            c3 = 0.0
        if math.isnan(c4):
            c4 = 0.0

        rows.append((int(category), symbol, dt, float(c1), float(c2), float(c3), float(c4)))

    return rows


def download_gbbq_zip(dest_zip: Path) -> None:
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(GBBQ_URL, timeout=120) as resp:
        data = resp.read()
    dest_zip.write_bytes(data)


def unzip_gbbq(zip_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    gbbq_path = dest_dir / "gbbq"
    if not gbbq_path.is_file():
        raise FileNotFoundError(f"解压后未找到 {gbbq_path}")
    return gbbq_path


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS tdx;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tdx.raw_gbbq (
                category BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                "date" DATE NOT NULL,
                c1 DOUBLE PRECISION,
                c2 DOUBLE PRECISION,
                c3 DOUBLE PRECISION,
                c4 DOUBLE PRECISION
            );
            """
        )
    conn.commit()


def import_rows(conn, rows: list[tuple], batch: int, truncate: bool) -> int:
    from psycopg2.extras import execute_values

    ensure_table(conn)
    with conn.cursor() as cur:
        if truncate:
            cur.execute("TRUNCATE TABLE tdx.raw_gbbq;")
    conn.commit()

    if not rows:
        return 0

    total = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i : i + batch]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO tdx.raw_gbbq (category, symbol, date, c1, c2, c3, c4)
                VALUES %s
                """,
                chunk,
            )
        total += len(chunk)
        conn.commit()
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="下载并导入 GBBQ → tdx.raw_gbbq（对齐 tdx2db update_gbbq）")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="PostgreSQL 连接 URL")
    parser.add_argument("--batch", type=int, default=5000, help="每批插入行数")
    parser.add_argument("--dry-run", action="store_true", help="只下载解析，不写数据库")
    parser.add_argument("--no-truncate", action="store_true", help="不 TRUNCATE（追加，可能与 tdx2db 行为不一致）")
    parser.add_argument("--cache-dir", type=str, default="", help="缓存目录（默认系统临时目录下子目录）")
    args = parser.parse_args()

    if not HEX_KEYS_FILE.is_file():
        print(f"错误：找不到 {HEX_KEYS_FILE}（TDX_daily/data/gbbq_hex_keys.txt）", file=sys.stderr)
        sys.exit(1)

    keys = load_keys()
    cache = Path(args.cache_dir) if args.cache_dir else Path(tempfile.mkdtemp(prefix="gbbq_"))
    zip_path = cache / "gbbq.zip"
    unzip_dir = cache / "gbbq-temp"

    print(f"下载: {GBBQ_URL}")
    download_gbbq_zip(zip_path)
    print(f"已保存: {zip_path} ({zip_path.stat().st_size:,} 字节)")

    if unzip_dir.exists():
        import shutil

        shutil.rmtree(unzip_dir, ignore_errors=True)
    gbbq_file = unzip_gbbq(zip_path, unzip_dir)
    print(f"解密解析: {gbbq_file}")

    rows = decode_gbbq_file(gbbq_file, keys)
    print(f"解析得到 {len(rows):,} 条（已按 GenerateSymbol 过滤）")

    if args.dry_run:
        if rows:
            print("样例前 3 条:", rows[:3])
        print("dry-run：未写入数据库")
        return

    import psycopg2

    conn = psycopg2.connect(args.db_url)
    try:
        n = import_rows(conn, rows, args.batch, truncate=not args.no_truncate)
        print(f"已写入 tdx.raw_gbbq: {n:,} 条（truncate={'否' if args.no_truncate else '是'}）")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
