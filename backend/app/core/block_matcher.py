#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
当日所走板块匹配器（向量 + 官方归属兜底）

匹配流程：
  1. 向量匹配（主）：涨停原因 vs 全量板块（dim_block），余弦相似度 × 板块强度，
     相似度低于阈值（0.5）的弱相关不参与。
  2. 官方归属兜底：向量无匹配时，用同花顺板块成分股（blocks.stock_codes）
     选当日强度最高的板块。

性能：板块向量持久化到文件（block_vec.json），个股 reason 向量跨请求缓存。
"""

import os as _os
import json as _json
import re
from typing import Dict, List, Optional


def is_pure_topic_block(block_name: str) -> bool:
    """过滤非题材板块（如"2026中报预增"）"""
    if re.search(r'\d{4}|预增|涨停|新高|超跌|次新|摘帽|退市|回购', block_name):
        return False
    return True


def block_strength(block: Dict, max_limit: int, max_change: float, max_cont: int) -> float:
    """板块当日强度（0~1）：涨停数 60% + 涨跌幅 25% + 连板家数 15%"""
    limit = float(block.get('limit_up_num') or 0)
    change = float(block.get('change_rate') or 0)
    cont = float(block.get('continuous_plate_num') or 0)

    norm_limit = limit / max_limit if max_limit > 0 else 0
    norm_change = max(0.0, min(1.0, change / max_change)) if max_change > 0 else 0
    norm_cont = cont / max_cont if max_cont > 0 else 0

    return 0.6 * norm_limit + 0.25 * norm_change + 0.15 * norm_cont


def strength_basis(blocks: List[Dict]) -> tuple:
    """计算强度归一化基准 (max_limit, max_change, max_cont)"""
    valid = [b for b in blocks if is_pure_topic_block(b.get('block_name') or '')] or blocks
    max_limit = max((float(b.get('limit_up_num') or 0) for b in valid), default=1)
    max_change = max((abs(float(b.get('change_rate') or 0)) for b in valid), default=1)
    max_cont = max((float(b.get('continuous_plate_num') or 0) for b in valid), default=1)
    return max_limit, max_change, max_cont


# 板块名 -> 向量（进程级缓存）
_block_vec_cache: Dict[str, List[float]] = {}

# reason 文本 -> 向量（跨请求缓存：同题材股票复用）
_reason_vec_cache: Dict[str, List[float]] = {}

# 向量匹配相似度阈值：低于此值的弱相关不算（避免被强板块带偏）
VEC_SIM_THRESHOLD = 0.5

# 板块向量文件缓存（持久化到挂载卷，避免进程重启后重算 417 个板块）
_BLOCK_VEC_FILE = _os.path.join(
    _os.environ.get('FASTEMBED_CACHE_PATH', '/root/.cache/fastembed'),
    'block_vec.json',
)


def _ensure_block_vecs(names: List[str]) -> bool:
    """补齐缺失板块的向量：内存缓存 → 文件缓存 → embedding 计算并落盘"""
    from app.core.embedding import embed_texts

    missing = [n for n in names if n and n not in _block_vec_cache]
    if not missing:
        return True

    file_cache: Dict[str, List[float]] = {}
    try:
        if _os.path.exists(_BLOCK_VEC_FILE):
            with open(_BLOCK_VEC_FILE, 'r', encoding='utf-8') as f:
                file_cache = _json.load(f)
    except Exception:
        pass

    still_missing = []
    for n in missing:
        v = file_cache.get(n)
        if v and len(v) >= 512:
            _block_vec_cache[n] = v
        else:
            still_missing.append(n)

    if still_missing:
        vecs = embed_texts(still_missing)
        if vecs is None:
            return False
        for n, v in zip(still_missing, vecs):
            _block_vec_cache[n] = v
        try:
            file_cache.update({n: _block_vec_cache[n] for n in still_missing})
            with open(_BLOCK_VEC_FILE, 'w', encoding='utf-8') as f:
                _json.dump(file_cache, f, ensure_ascii=False)
        except Exception:
            pass
    return True


def _ensure_reason_vec(reason_text: str) -> Optional[List[float]]:
    """个股 reason 向量（跨请求缓存：同题材股票复用）"""
    from app.core.embedding import embed_texts

    if reason_text in _reason_vec_cache:
        return _reason_vec_cache[reason_text]
    vecs = embed_texts([reason_text])
    if not vecs:
        return None
    _reason_vec_cache[reason_text] = vecs[0]
    return vecs[0]


def _to_result(block: Dict, match: float, strength: float, score: float, matched_tag: str) -> Dict:
    return {
        'block_name': block.get('block_name') or '',
        'match': round(match, 3),
        'strength': round(strength, 3),
        'score': round(score, 4),
        'matched_tag': matched_tag,
        'limit_up_num': block.get('limit_up_num') or 0,
        'continuous_plate_num': block.get('continuous_plate_num') or 0,
        'change_rate': float(block.get('change_rate') or 0),
    }


def pick_trend_block_vec(stock_code: str, reason_text: str, blocks: List[Dict]) -> Optional[Dict]:
    """
    向量匹配：个股涨停原因 vs 全量板块，余弦相似度 × 板块强度 选最佳板块。

    板块向量：内存 → 文件缓存 → embedding（落盘持久化）。
    个股 reason 向量：跨请求缓存（同题材复用）。
    embedding 不可用或全部低于阈值时返回 None。
    """
    if not blocks or not reason_text:
        return None

    # "+" 是同花顺涨停原因的常规分隔符，向量化前规范化为空格，
    # 避免把 "+" 当作字符参与语义匹配（如 连锁零售+新零售+半年报增长）
    reason_text = reason_text.replace('+', ' ').strip()
    if not reason_text:
        return None

    # 1. 补齐缺失板块的向量
    names = [b.get('block_name') or '' for b in blocks]
    if not _ensure_block_vecs(names):
        return None  # embedding 不可用

    # 2. 个股 reason 向量（缓存）
    sv = _ensure_reason_vec(reason_text)
    if sv is None:
        return None

    # 3. 全量板块余弦 × 强度（numpy 向量化：一次矩阵乘法替代逐板块 Python 循环）
    import numpy as np

    topic_blocks = [
        b for b in blocks
        if is_pure_topic_block(b.get('block_name') or '')
        and b.get('block_name') in _block_vec_cache
    ]
    if not topic_blocks:
        return None

    mat = np.array(
        [_block_vec_cache[b['block_name']] for b in topic_blocks],
        dtype=np.float32,
    )  # (K, 512)，已归一化
    sims = mat @ np.array(sv, dtype=np.float32)  # (K,) 余弦

    hit_idx = np.where(sims >= VEC_SIM_THRESHOLD)[0]
    if len(hit_idx) == 0:
        return None

    max_limit, max_change, max_cont = strength_basis(blocks)

    # 语义主导：先取相似度最高分；仅当其他板块与最高分差距很小(≤0.03)时，
    # 才用强度加权 score 决胜。避免"高 sim 但当日无表现的板块"被
    # 强度加权反超（如 零售0.673 vs 数字经济0.527，数字经济靠强度翻盘）。
    max_sim = float(sims[hit_idx].max())
    tie_window = 0.03

    best = None
    for i in hit_idx:
        b = topic_blocks[int(i)]
        sim = float(sims[i])
        if sim < max_sim - tie_window:
            continue  # 语义差距明显，不参与强度竞争
        strength = block_strength(b, max_limit, max_change, max_cont)
        score = sim * (0.5 + 0.5 * strength)
        if best is None or score > best['score']:
            result = _to_result(
                b, sim, strength, score,
                f'语义相似 {round(sim * 100)}%'
            )
            result['vec'] = True
            best = result
    return best


def pick_official_block(stock_code: str, blocks: List[Dict]) -> Optional[Dict]:
    """
    官方归属兜底：同花顺板块成分股（blocks.stock_codes）包含该股的板块中，
    选当日强度最高的。
    """
    if not blocks:
        return None

    max_limit, max_change, max_cont = strength_basis(blocks)
    best = None
    for b in blocks:
        name = b.get('block_name') or ''
        if not is_pure_topic_block(name):
            continue
        if str(stock_code) in [str(c) for c in (b.get('stock_codes') or [])]:
            strength = block_strength(b, max_limit, max_change, max_cont)
            if best is None or strength > best['strength']:
                best = _to_result(
                    b, 1.0, strength, strength,
                    '[同花顺板块归属]'
                )
    return best


def _rank_factor(rank: int) -> float:
    """东财相关度排名 → 权重：rank1=1.0，越靠后越低（最低 0.15）"""
    return max(0.15, 1.0 - (rank - 1) * 0.08)


def pick_trend_blocks_em(stock_code: str, blocks: List[Dict], em_boards: Optional[List[tuple]] = None, top_n: int = 3) -> List[Dict]:
    """
    东财归属选"当日最相关板块"（Top N）：
    - 候选 = 东财返回的所属板块 ∩ 当日板块（dim_block/block_top）
    - score = 东财 rank 权重 × (0.5 + 0.5 × 板块当日强度)
    - 返回按 score 降序的前 top_n 个
    """
    if not em_boards:
        return []
    by_name = {b.get('block_name'): b for b in blocks}
    candidates = []
    for name, rank in em_boards:
        b = by_name.get(name)
        if b and is_pure_topic_block(name):
            candidates.append((name, rank, b))
    if not candidates:
        # 无交集：东财 rank 最靠前且存在于候选池的板块
        for name, rank in em_boards:
            b = by_name.get(name)
            if b:
                candidates.append((name, rank, b))
                break
    if not candidates:
        return []

    max_limit, max_change, max_cont = strength_basis(blocks)
    scored = []
    for name, rank, b in candidates:
        strength = block_strength(b, max_limit, max_change, max_cont)
        score = _rank_factor(rank) * (0.5 + 0.5 * strength)
        result = _to_result(b, 1.0, strength, score, f'东财归属 rank{rank}')
        result['em'] = True
        scored.append(result)
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_n]


def pick_trend_block(stock_code: str, reason_text: str, blocks: List[Dict]) -> Optional[Dict]:
    """统一入口：向量优先，官方归属兜底。

    涨停原因为空/占位(未分类)时直接返回 None，不做官方归属兜底——
    未分类股票不应展示任何"所走板块"，避免误导。
    """
    reason_text = (reason_text or '').strip()
    if not reason_text or reason_text in ('未分类', '无', '-'):
        return None
    trend = None
    try:
        trend = pick_trend_block_vec(stock_code, reason_text, blocks)
    except Exception:
        trend = None
    if trend is None:
        trend = pick_official_block(stock_code, blocks)
    return trend
