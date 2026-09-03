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
    全部失败返回 (None, None)。
    """
    model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    for source, url, key in _provider_list():
        if not key:
            continue
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
            if resp.status_code != 200:
                print(f"[LLM {source}] HTTP {resp.status_code}: {resp.text[:200]}")
                continue
            result = resp.json()
            content = (result.get('choices') or [{}])[0].get('message', {}).get('content', '')
            if content:
                return content, source
            print(f"[LLM {source}] 返回内容为空")
        except Exception as e:
            print(f"[LLM {source}] 调用异常: {e}")
            continue
    return None, None
