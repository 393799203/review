#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文文本向量化（bge-small-zh-v1.5，本地 ONNX 推理，完全离线）

模型文件由 scripts/fetch_dim_blocks.py 预下载到 FASTEMBED_CACHE_PATH 挂载卷。
失败时返回 None，调用方回退到官方归属匹配。
"""

import os
from typing import List, Optional


def _get_embedder():
    os.environ.setdefault('FASTEMBED_CACHE_PATH', '/root/.cache/fastembed')
    from app.core.bge_embedder import get_embedder
    return get_embedder()


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """批量文本向量化；失败返回 None"""
    texts = [t for t in (texts or []) if t]
    if not texts:
        return []
    try:
        emb = _get_embedder()
        if emb is None:
            return None
        return emb.embed(texts)
    except Exception as e:
        print(f"⚠️ embedding 失败（回退官方归属）: {e}")
        return None


def embedding_available() -> bool:
    try:
        return _get_embedder() is not None
    except Exception:
        return False
