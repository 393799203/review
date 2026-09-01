"""
将 vipdoc/refmhq 下官网日线增量 .md1/.cod 合并为各股 .day（与原 tdx2db NativeDayMerge 对齐）。

纯 Python 实现，无需通达信 datatool 二进制。
"""
from __future__ import annotations

import logging
import struct
import time
from pathlib import Path
from typing import NamedTuple

LOG = logging.getLogger(__name__)


def _flush_logging() -> None:
    for h in logging.root.handlers:
        try:
            h.flush()
        except OSError:
            pass

COD_RECORD_SIZE = 150
MD1_BLOCK_SIZE = 512
RECORD_SIZE = 32
# 与 tdx_import_daily_bar.DAY_RECORD_FMT 一致
DAY_PACK_FMT = "<IIIIIfII"


class Md1OHLCV(NamedTuple):
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


def parse_incr_filename(name: str) -> tuple[str, int]:
    """``sh260318.md1`` → (\"sh\", 20260318)。解析失败则抛 ValueError。"""
    base = name.split(".", 1)[0]
    if len(base) < 8:
        raise ValueError(f"filename too short: {name}")
    exchange = base[:2]
    date_str = base[2:]
    if len(date_str) != 6:
        raise ValueError(f"invalid date part in filename: {date_str}")
    yy = int(date_str[0]) * 10 + int(date_str[1])
    mm = int(date_str[2]) * 10 + int(date_str[3])
    dd = int(date_str[4]) * 10 + int(date_str[5])
    year = 2000 + yy
    if year > 2080:
        year -= 100
    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        raise ValueError(f"invalid date: {year}-{mm:02d}-{dd:02d}")
    return exchange, year * 10000 + mm * 100 + dd


def parse_cod_entries(cod_path: Path) -> list[tuple[str, int]]:
    data = cod_path.read_bytes()
    if len(data) % COD_RECORD_SIZE != 0:
        raise ValueError(
            f"invalid cod file size {len(data)} (not divisible by {COD_RECORD_SIZE})"
        )
    out: list[tuple[str, int]] = []
    for i in range(len(data) // COD_RECORD_SIZE):
        off = i * COD_RECORD_SIZE
        rec = data[off : off + COD_RECORD_SIZE]
        code = rec[0:6].decode("ascii", errors="ignore").rstrip("\x00 ")
        if not code:
            continue
        seq = struct.unpack_from("<H", rec, 32)[0]
        out.append((code, seq))
    return out


def read_md1_block(md1_data: bytes, seq_num: int) -> Md1OHLCV:
    offset = seq_num * MD1_BLOCK_SIZE
    if offset + MD1_BLOCK_SIZE > len(md1_data):
        raise ValueError(f"md1 offset {offset} out of range (size {len(md1_data)})")
    blk = md1_data[offset : offset + MD1_BLOCK_SIZE]
    o, h, l, c = struct.unpack_from("<dddd", blk, 12)
    vol = struct.unpack_from("<I", blk, 56)[0]
    amt = struct.unpack_from("<d", blk, 72)[0]
    return Md1OHLCV(o, h, l, c, vol, amt)


def make_day_record(date_yyyymmdd: int, rec: Md1OHLCV) -> bytes:
    return struct.pack(
        DAY_PACK_FMT,
        date_yyyymmdd,
        round(rec.open * 100),
        round(rec.high * 100),
        round(rec.low * 100),
        round(rec.close * 100),
        rec.amount,
        rec.volume,
        0,
    )


def append_day_record(path: Path, date_yyyymmdd: int, record: bytes) -> None:
    try:
        st = path.stat()
    except FileNotFoundError:
        st = None
    if st is not None and st.st_size >= RECORD_SIZE:
        with path.open("rb") as f:
            f.seek(st.st_size - RECORD_SIZE)
            last_rec = f.read(RECORD_SIZE)
        last_date = struct.unpack_from("<I", last_rec, 0)[0]
        if last_date >= date_yyyymmdd:
            return
    with path.open("ab") as f:
        f.write(record)


def merge_single_day(
    vipdoc_dir: Path, exchange: str, date_yyyymmdd: int, cod_file: Path, md1_file: Path
) -> None:
    entries = parse_cod_entries(cod_file)
    md1_data = md1_file.read_bytes()
    lday_dir = vipdoc_dir / exchange / "lday"
    lday_dir.mkdir(parents=True, exist_ok=True)

    for stock_code, seq_num in entries:
        try:
            ohlcv = read_md1_block(md1_data, seq_num)
        except ValueError:
            continue
        if ohlcv.volume == 0 and ohlcv.amount == 0:
            continue
        if ohlcv.open <= 0 or ohlcv.close <= 0:
            continue
        day_path = lday_dir / f"{exchange}{stock_code}.day"
        day_rec = make_day_record(date_yyyymmdd, ohlcv)
        try:
            append_day_record(day_path, date_yyyymmdd, day_rec)
        except OSError:
            continue


def native_day_merge(vipdoc_dir: Path | str) -> None:
    """
    扫描 ``vipdoc/refmhq/*.md1``，与同名的 ``.cod`` 配对，写入 ``vipdoc/{sh|sz|bj}/lday/*.day``。
    """
    vipdoc = Path(vipdoc_dir)
    refmhq = vipdoc / "refmhq"
    if not refmhq.is_dir():
        LOG.debug("native_day_merge: refmhq 不存在 %s", refmhq)
        return

    md1_files = sorted(refmhq.glob("*.md1"))
    if not md1_files:
        LOG.debug("native_day_merge: 无 .md1 文件 %s", refmhq)
        return

    to_process: list[Path] = []
    for md1_file in md1_files:
        cod_file = refmhq / (md1_file.stem + ".cod")
        if not cod_file.is_file():
            continue
        try:
            parse_incr_filename(md1_file.name)
        except ValueError:
            continue
        to_process.append(md1_file)

    n = len(to_process)
    if n == 0:
        LOG.debug("native_day_merge: 无可用 .md1/.cod 对 %s", refmhq)
        return

    LOG.info(
        "native_day_merge: 将处理 %d 个交易日文件（refmhq 内全部历史，不仅是刚下载的 zip），"
        "磁盘写入多时会较慢，请等待…",
        n,
    )
    _flush_logging()

    t0 = time.perf_counter()
    step = 1 if n <= 30 else max(1, n // 25)
    for i, md1_file in enumerate(to_process, 1):
        cod_file = refmhq / (md1_file.stem + ".cod")
        exchange, date_val = parse_incr_filename(md1_file.name)
        if i == 1 or i == n or (i % step == 0):
            LOG.info(
                "native_day_merge: [%d/%d] %s（已用时 %.0fs）",
                i,
                n,
                md1_file.name,
                time.perf_counter() - t0,
            )
            _flush_logging()
        try:
            merge_single_day(vipdoc, exchange, date_val, cod_file, md1_file)
        except (OSError, ValueError) as e:
            raise RuntimeError(f"merge {md1_file.name} failed: {e}") from e

    LOG.info(
        "native_day_merge 完成: %s（共 %d 个交易日，用时 %.0fs）",
        vipdoc,
        n,
        time.perf_counter() - t0,
    )
    _flush_logging()
