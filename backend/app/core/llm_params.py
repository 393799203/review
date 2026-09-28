#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM 请求参数统一构造。

为什么需要这个模块（2026-09-28 实测，网关 https://token.wasu.cn/v1）：

1. `deepseek-v4.x` 都是**推理模型**：先输出 `reasoning_content`，再输出正文 `content`。
   对「按要求抽取/归并成 JSON」这类任务，推理会吃掉大量预算甚至全部预算，表现为
   `finish_reason=length` 且 `content` 为空，业务端报「AI 返回格式解析失败」。
   实测关键词归并 prompt：4096 预算 → content=0（4096 全给推理）；
   16000 预算 → 仍 content=0，推理耗尽 16000、耗时 149s。

2. 该网关支持 `enable_thinking=false` 关闭思考，同一 prompt 效果：
   31.1s / 推理 3005 token  →  2~4s / 推理 0 token，JSON 正常返回。
   （`thinking={"type":"disabled"}`、`reasoning_effort="none"` 同样有效，取最常见写法）

3. 旧的 `timeout=60` 对推理模型偏短（个股分析实测 40s+），统一改为可配置。

因此所有调用点都应通过本模块构造 payload，不要再各自硬编码。
"""
import os

_TRUE_VALUES = {"1", "true", "yes", "on"}


def thinking_disabled() -> bool:
    """是否关闭模型思考。默认关闭：推理模型在 JSON 抽取类任务上既慢又易截断。

    需要推理质量时在 .env 设 `DEEPSEEK_DISABLE_THINKING=false`，
    并相应调大 `DEEPSEEK_MAX_TOKENS_*`（否则正文会被推理挤空）。
    """
    return os.environ.get("DEEPSEEK_DISABLE_THINKING", "true").strip().lower() in _TRUE_VALUES


def request_timeout(default: int = 120) -> int:
    """读超时（秒）。可用 DEEPSEEK_TIMEOUT 覆盖。"""
    try:
        value = int(os.environ.get("DEEPSEEK_TIMEOUT", str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def build_payload(model: str, messages: list, temperature: float = 0.7,
                  max_tokens: int = 2048, stream: bool = False,
                  disable_thinking: bool = None) -> dict:
    """构造 OpenAI 兼容的 chat/completions 请求体。"""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if stream:
        payload["stream"] = True
    off = thinking_disabled() if disable_thinking is None else disable_thinking
    if off:
        payload["enable_thinking"] = False
    return payload