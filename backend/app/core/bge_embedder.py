#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bge-small-zh-v1.5 自定义 ONNX 加载器

直接加载本地 ONNX 模型 + tokenizer（不经 huggingface_hub/fastembed 的下载逻辑），
完全离线。模型文件由 scripts/fetch_dim_blocks.py 或手动下载到
FASTEMBED_CACHE_PATH 指向的目录（models--Qdrant--bge-small-zh-v1.5/snapshots/*/）。
"""

import os
from typing import List, Optional

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer


def find_model_dir(cache_dir: Optional[str] = None) -> Optional[str]:
    """在缓存目录中查找 Qdrant/bge-small-zh-v1.5 模型目录"""
    base = cache_dir or os.environ.get('FASTEMBED_CACHE_PATH') or '/root/.cache/fastembed'
    snapshot_root = os.path.join(base, 'models--Qdrant--bge-small-zh-v1.5', 'snapshots')
    if not os.path.isdir(snapshot_root):
        return None
    for name in os.listdir(snapshot_root):
        model_dir = os.path.join(snapshot_root, name)
        if os.path.isfile(os.path.join(model_dir, 'model_optimized.onnx')):
            return model_dir
    return None


class BgeEmbedder:
    """bge 系列 ONNX 推理（CLS pooling + L2 归一化，与 fastembed 一致）"""

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.tokenizer = Tokenizer.from_file(os.path.join(model_dir, 'tokenizer.json'))
        self.session = ort.InferenceSession(
            os.path.join(model_dir, 'model_optimized.onnx'),
            providers=['CPUExecutionProvider'],
        )
        self.input_names = [i.name for i in self.session.get_inputs()]

    def embed(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        results: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            encodings = self.tokenizer.encode_batch(batch)
            max_len = max((len(e.ids) for e in encodings), default=1)

            input_ids = []
            attention_mask = []
            for e in encodings:
                pad = max_len - len(e.ids)
                input_ids.append(e.ids + [0] * pad)
                attention_mask.append(e.attention_mask + [0] * pad)

            feeds = {
                'input_ids': np.array(input_ids, dtype=np.int64),
                'attention_mask': np.array(attention_mask, dtype=np.int64),
            }
            if 'token_type_ids' in self.input_names:
                feeds['token_type_ids'] = np.zeros_like(feeds['input_ids'])

            out = self.session.run(None, feeds)[0]  # (batch, seq, 512)
            if out.ndim == 3:
                vecs = out[:, 0]  # CLS
            else:
                vecs = out

            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs = vecs / np.maximum(norms, 1e-9)
            results.extend(vecs.astype(float).tolist())
        return results


_embedder = None


def get_embedder() -> Optional[BgeEmbedder]:
    global _embedder
    if _embedder is None:
        model_dir = find_model_dir()
        if model_dir is None:
            print('⚠️ 未找到 bge-small-zh-v1.5 模型目录（请先下载模型）')
            return None
        _embedder = BgeEmbedder(model_dir)
    return _embedder
