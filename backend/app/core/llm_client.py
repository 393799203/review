#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import re
import requests
from typing import Optional, Dict


class LLMClient:
    """DeepSeek 官方 API 客户端"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    @property
    def _chat_url(self) -> str:
        """base_url 允许配置为完整端点（.../v1/chat/completions）或 API 根（.../v1）"""
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def chat(self, messages: list, temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
        """通用对话接口（公开方法，供各业务复用）"""
        return self._chat(messages, temperature=temperature, max_tokens=max_tokens)

    def _chat(self, messages: list, temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
        if not self.api_key:
            raise ValueError("DeepSeek API Key 未配置，请在环境变量中设置 DEEPSEEK_API_KEY")

        try:
            url = self._chat_url
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()

            result = resp.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            raise RuntimeError("DeepSeek API 请求超时")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"DeepSeek API HTTP 错误: {e.response.status_code}")
        except Exception as e:
            raise RuntimeError(f"DeepSeek API 调用失败: {str(e)}")

    def find_comparable_stocks(self, user_query: str, hot_data: dict, context: dict, window_dates: list) -> dict:
        system_prompt = """你是一个A股对标股票分析助手。用户想要找与某只股票对标的其他股票。

我会提供同花顺热点数据（来自 zx.10jqka.com.cn/event/api/getharden），数据中包含涨停股票的代码、名称、涨幅、题材标签(reason)等信息。

请你根据用户的查询需求，结合提供的热点数据，自由回答用户的问题。输出请用Markdown格式，表格要清晰美观。

重要规则：
1. 只使用我提供的数据，不要编造任何数据
2. 不要使用网页搜索
3. 如果数据中没有找到相关信息，如实告知用户
4. 结果尽量用表格呈现，格式：股票代码 | 股票名称 | 日期 | 涨幅 | 题材标签
5. 在回答的最后，附加一个 [STOCKS_JSON]...[/STOCKS_JSON] 块，将你表格中提到的所有标的股票用JSON数组列出，格式：
[STOCKS_JSON]
[{"code":"603137","name":"恒尚节能","date":"2026-06-30","change_pct":"10.0","reason":"拟收购存储公司+建筑幕墙","category":"核心逻辑对标"}]
[/STOCKS_JSON]
字段说明：code=股票代码(纯数字,不带.SH/.SZ后缀), name=股票名称, date=涨停日期(YYYY-MM-DD), change_pct=涨幅(纯数字,去掉%号), reason=题材标签, category=对标角度(必须是以下三个值之一: "最直接对标"、"核心逻辑对标"、"其他相关对标")
如果表格中没有对标股票，输出空数组 []"""

        context_parts = []
        if context.get("stock_code"):
            context_parts.append(f"股票代码：{context['stock_code']}")
        if context.get("stock_name"):
            context_parts.append(f"股票名称：{context['stock_name']}")
        if context.get("block_name"):
            context_parts.append(f"所属板块：{context['block_name']}")
        if context.get("reason"):
            context_parts.append(f"题材标签：{context['reason']}")

        context_str = "\n".join(context_parts) if context_parts else "无上下文信息"

        hot_data_str = json.dumps(hot_data, ensure_ascii=False, indent=2)

        if len(hot_data_str) > 80000:
            truncated = {}
            for d in list(hot_data.keys())[:max(5, len(window_dates))]:
                truncated[d] = hot_data[d][:200]
            hot_data_str = json.dumps(truncated, ensure_ascii=False, indent=2)
            hot_data_str += "\n\n(数据已截断，只保留最近几个交易日)"

        user_prompt = f"""对标股票信息：
{context_str}

用户查询需求：{user_query}

同花顺热点数据：
```json
{hot_data_str}
```

请根据用户的查询需求，分析数据并回答。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        analysis = self._chat(messages, temperature=0.3, max_tokens=4096)

        stocks = []
        match = re.search(r'\[STOCKS_JSON\]\s*([\s\S]*?)\s*\[/STOCKS_JSON\]', analysis)
        if match:
            try:
                stocks = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        analysis = re.sub(r'\[STOCKS_JSON\][\s\S]*?\[/STOCKS_JSON\]', '', analysis).strip()

        return {
            "analysis": analysis,
            "stocks": stocks,
            "dates_queried": window_dates,
            "hot_data_count": sum(len(v) for v in hot_data.values())
        }

    def generate_wencai_query(self, user_input: str, context: dict) -> dict:
        system_prompt = """你是一个股票对标分析助手。用户想要找与某只股票对标的其他股票。

你的任务是将用户的自然语言查询转化为同花顺问财（iwencai）的查询语句。

问财查询语法要求：
1. 使用中文自然语言描述筛选条件
2. 支持的条件包括：板块、行业、市值、市盈率、涨跌幅、成交量、换手率、涨停次数等
3. 多个条件用逗号或句号连接

返回格式要求：只返回一个JSON对象，格式为：
{
  "wencai_query": "问财查询语句",
  "explanation": "对这个查询的解释说明"
}

不要返回其他内容。"""

        context_parts = []
        if context.get("stock_name"):
            context_parts.append(f"股票名称：{context['stock_name']}")
        if context.get("stock_code"):
            context_parts.append(f"股票代码：{context['stock_code']}")
        if context.get("block_name"):
            context_parts.append(f"所属板块：{context['block_name']}")
        if context.get("reason"):
            context_parts.append(f"涨停原因：{context['reason']}")

        context_str = "；".join(context_parts) if context_parts else "无上下文信息"

        user_prompt = f"""当前对标股票信息：
{context_str}

用户查询需求：{user_input}

请根据以上信息，生成一个问财查询语句，用于找到与目标股票对标的其他股票。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        raw_response = self._chat(messages, temperature=0.3, max_tokens=1024)

        try:
            result = json.loads(raw_response.strip())
            if "wencai_query" not in result:
                result["wencai_query"] = raw_response
                result["explanation"] = "LLM 返回格式异常，已使用原始输出作为查询"
            return result
        except json.JSONDecodeError:
            return {
                "wencai_query": user_input,
                "explanation": f"AI 分析结果无法解析，将使用原始输入查询。原始回复: {raw_response[:200]}"
            }


llm_client = LLMClient()
