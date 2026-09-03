#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 聊天统一入口（带后备通道）

主通道：DeepSeek（DEEPSEEK_API_URL / DEEPSEEK_API_KEY / DEEPSEEK_MODEL）
后备通道：SenseNova（LLM_FALLBACK_API_URL / LLM_FALLBACK_API_KEY），
模型名沿用 DEEPSEEK_MODEL（模型不变）。

主通道请求失败（网络错误 / 非200 / 内容为空）时自动切换后备通道。
返回 (content, source)；source ∈ {'deepseek', 'fallback', None}。
"""

import os
import requests

DEFAULT_DEEPSEEK_URL = 'https://api.deepseek.com/v1/chat/completions'
DEFAULT_FALLBACK_URL = 'https://token.sensenova.cn/v1/chat/completions'


def _provider_list():
    providers = [
        ('deepseek', os.environ.get('DEEPSEEK_API_URL') or DEFAULT_DEEPSEEK_URL,
         os.environ.get('DEEPSEEK_API_KEY')),
        ('fallback', os.environ.get('LLM_FALLBACK_API_URL') or DEFAULT_FALLBACK_URL,
         os.environ.get('LLM_FALLBACK_API_KEY')),
    ]
    return providers


def chat_completions(messages, temperature=0.7, max_tokens=1000, timeout=120):
    """
    依次尝试主通道与后备通道，返回 (content, source)。
    对 429/503 等瞬时限流错误做短退避重试（最多 RETRY_TIMES 次）。
    全部失败返回 (None, None)。
    """
    import time
    model = os.environ.get('LLM_FALLBACK_MODEL') or os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    RETRY_TIMES = 2  # 限流后额外重试次数
    for source, url, key in _provider_list():
        if not key:
            continue
        last_err = None
        for attempt in range(RETRY_TIMES + 1):
            try:
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    result = resp.json()
                    content = (result.get('choices') or [{}])[0].get('message', {}).get('content', '')
                    if content:
                        return content, source
                    print(f"[LLM {source}] 返回内容为空")
                    last_err = 'empty'
                    break
                # 429/503 限流或服务繁忙：退避重试；其余状态码直接放弃该通道
                if resp.status_code in (429, 503) and attempt < RETRY_TIMES:
                    wait = 3 * (attempt + 1)
                    print(f"[LLM {source}] HTTP {resp.status_code} 限流，{wait}s 后重试 "
                          f"({attempt + 1}/{RETRY_TIMES}): {resp.text[:120]}")
                    time.sleep(wait)
                    continue
                print(f"[LLM {source}] HTTP {resp.status_code}: {resp.text[:200]}")
                last_err = f'http{resp.status_code}'
                break
            except Exception as e:
                print(f"[LLM {source}] 调用异常: {e}")
                last_err = str(e)
                if attempt < RETRY_TIMES:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
        if last_err != 'empty':
            print(f"[LLM {source}] 放弃（{last_err}）")
    return None, None
