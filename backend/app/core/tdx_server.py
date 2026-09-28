#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通达信行情服务器探测与固定。

背景（2026-09-28 实测，服务器 124.221.228.215）：

- mootdx 未配置 `BESTIP` 时会用它内置 HQ 列表里"最快/第一台"的节点（本机实测选中
  `180.153.18.170:7709`），而**该节点能 TCP 连上、quotes/bars 却返回空数据**。
  于是 `get_realtime_quote` / `get_stock_kline` 全部静默落空，一直靠新浪/腾讯兜底，
  表象很像"通达信 quotes 协议被服务器拒绝"，其实只是选错了节点。

- 遍历 tdxpy 内置的 104 家行情服务器实测：**仅 8 家真正可用**，全部是国泰君安
  `117.34.114.13~20 / .27:7709`，quotes 与 bars 均正常，且价格与新浪一致（茅台 1243.88）。

- mootdx 的 `StdQuotes.__init__` 收到 `server=` 参数时会把它写进 `BESTIP`
  （配置文件 `/root/.mootdx/config.json`），之后所有 `Quotes.factory(...)` 调用都会复用。
  因此在启动时探测并固定一台可用节点即可，**无需改动各处调用点**。

配置：`TDX_SERVER=ip:port,ip:port,...` 自定义候选与顺序；不配则用下面实测可用的列表。
"""
import os
from typing import List, Optional, Tuple

# 实测可用节点（2026-09-28 全量扫描 104 家中仅这 8 家返回数据）
DEFAULT_SERVERS: List[Tuple[str, int]] = [
    ("117.34.114.13", 7709),
    ("117.34.114.14", 7709),
    ("117.34.114.15", 7709),
    ("117.34.114.16", 7709),
    ("117.34.114.17", 7709),
    ("117.34.114.18", 7709),
    ("117.34.114.20", 7709),
    ("117.34.114.27", 7709),
]

# 探测用的标的（贵州茅台，沪市）
PROBE_MARKET = 1
PROBE_CODE = "600519"

_selected: Optional[Tuple[str, int]] = None


def parse_servers(raw: str) -> List[Tuple[str, int]]:
    """解析 `ip:port,ip:port` 形式的环境变量值。"""
    out: List[Tuple[str, int]] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        ip, _, port = part.partition(":")
        try:
            out.append((ip.strip(), int(port)))
        except ValueError:
            continue
    return out


def candidates() -> List[Tuple[str, int]]:
    """候选节点：环境变量优先，其后是内置实测可用列表（去重保序）。"""
    out: List[Tuple[str, int]] = []
    for item in parse_servers(os.environ.get("TDX_SERVER", "")) + DEFAULT_SERVERS:
        if item not in out:
            out.append(item)
    return out


def probe(ip: str, port: int, timeout: float = 3.0) -> bool:
    """节点可用性判定：能连上 **且** quotes 返回非空（很多节点能连但返回空）。"""
    from tdxpy.hq import TdxHq_API

    api = TdxHq_API(heartbeat=False)
    try:
        if not api.connect(ip, port, time_out=timeout):
            return False
        return bool(api.get_security_quotes([(PROBE_MARKET, PROBE_CODE)]))
    except Exception:
        return False
    finally:
        try:
            api.disconnect()
        except Exception:
            pass


def ensure_tdx_server(timeout: float = 3.0, max_probe: int = 6, verbose: bool = True) -> Optional[Tuple[str, int]]:
    """探测并固定一台可用的通达信行情服务器，返回 (ip, port)；全部不可用返回 None。

    固定方式：`Quotes.factory(market='std', server=...)` —— mootdx 会自行写入 BESTIP，
    后续所有不带 server 参数的 factory 调用都会复用该节点。
    """
    global _selected
    if _selected is not None:
        return _selected

    for ip, port in candidates()[:max_probe]:
        if not probe(ip, port, timeout=timeout):
            if verbose:
                print(f"✗ 通达信节点 {ip}:{port} 无数据，试下一个")
            continue
        try:
            from mootdx.quotes import Quotes

            client = Quotes.factory(market="std", server=(ip, port))
            _selected = (ip, port)
            if verbose:
                print(f"✓ 通达信行情节点已固定: {ip}:{port}（mootdx BESTIP 已更新）")
            return _selected
        except Exception as e:
            if verbose:
                print(f"✗ 固定通达信节点 {ip}:{port} 失败: {type(e).__name__}: {e}")
            continue

    if verbose:
        print("✗ 未找到可用的通达信行情节点，将使用新浪/腾讯兜底数据源")
    return None


def make_client(market="std"):
    """创建 mootdx 客户端 —— 统一入口，确保先固定可用节点再连接。

    注意：不能只在启动时固定一次。`app.py` 在 **import 阶段**就创建了模块级
    `data_fetcher = DataFetcher()`，早于 `__main__` 里的启动逻辑；而一个已建立的
    mootdx 客户端会一直连着当时那台（可能是返回空数据的）节点。
    因此所有 `Quotes.factory(...)` 调用都应改走这里。
    """
    from mootdx.quotes import Quotes

    server = ensure_tdx_server()
    if server:
        return Quotes.factory(market=market, server=server)
    return Quotes.factory(market=market)