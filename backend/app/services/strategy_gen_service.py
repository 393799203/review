#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略代码生成服务

用户输入自然语言选股/量化条件，调用 DeepSeek 生成自包含可运行的
Python 策略脚本（psycopg2 + pandas，读 TDX 行情库）。

安全说明：本服务只生成代码文本，服务端不执行任何生成的代码，
脚本由用户下载后在本地自行运行。
"""

import re
from typing import Dict, Optional, Tuple

from app.core.llm_client import LLMClient

# 数据环境说明（固定写入 system prompt，与 TDX 库实际结构保持一致）
DATA_ENV_DOC = """PostgreSQL，连接串从环境变量 DB_URL 读取（psycopg2 + pandas，pd.read_sql），schema 为 tdx：
- tdx.raw_stocks_daily(symbol, date, open, high, low, close, amount, volume)；symbol 形如 'sh600519'/'sz000001'/'bj920238'；volume 单位是「手」（1 手 = 100 股）
- tdx.raw_stocks_basic(date, symbol, close, preclose, change_pct, amplitude, turnover, floatmv, totalmv)；change_pct/turnover/amplitude 为百分比数值；floatmv/totalmv 单位万元
- tdx.v_hfq_daily / tdx.v_qfq_daily / tdx.v_bfq_daily：后复权/前复权/不复权日线视图（含 OHLC、preclose、turnover 等）。回测用 v_hfq_daily 避免未来函数；qfq 以最新日为基准
- tdx.dim_sw_industry(symbol, code, name, market, sw1_code, sw1_name, sw2_code, sw2_name, sw3_code, sw3_name, start_date, end_date, is_latest)：申万行业维表，含历史归属（is_latest=1 为当前）
- tdx.v_sw_industry_daily(date, sw1_code, sw1_name, sw2_code, sw2_name, stock_count, avg_change_pct)：行业日聚合，sw2_code 为 NULL 的行是申万一级"""

BACKTEST_REQUIREMENT = """6. 在脚本末尾附加一个简单向量化回测段：对筛选出的股票，统计买入后持有 N 日
   （N 放顶部常量区）的收益率分布（均值/中位数/胜率等）并打印。回测假设用注释注明：
   T+1 日开盘价买入、不计手续费滑点；回测统一使用 tdx.v_hfq_daily 后复权数据避免未来函数。"""


class StrategyGenService:
    """策略代码生成服务类"""

    def __init__(self):
        self.llm_client = LLMClient()

    def generate_strategy(self, requirement: str, with_backtest: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        根据自然语言条件生成策略代码

        Args:
            requirement: 用户输入的选股/量化条件描述
            with_backtest: 是否附加简单向量化回测段

        Returns:
            tuple: (success, message, {'code': ..., 'model': ...})
        """
        requirement = (requirement or '').strip()
        if not requirement:
            return False, '请填写选股/量化条件描述', None
        if len(requirement) > 2000:
            return False, '条件描述过长（不超过 2000 字）', None

        if not self.llm_client.api_key:
            raise ValueError('DeepSeek API Key 未配置，请在环境变量中设置 DEEPSEEK_API_KEY')

        system_prompt = f"""你是一个 A 股量化策略代码生成助手。根据用户的自然语言选股/量化条件，
生成一个自包含、可直接运行的 Python 策略脚本。

数据环境（脚本必须严格按此结构访问数据）：
{DATA_ENV_DOC}

输出要求：
1. 只输出一个 ```python 代码块，不要输出任何解释性文字。
2. 脚本必须自包含可运行：import 齐全，连接串从环境变量 DB_URL 读取，
   包含 if __name__ == '__main__': 入口，运行后打印筛选结果（含股票代码、名称、关键指标）。
3. 筛选条件的参数（日期、倍数、窗口天数等）一律放在文件顶部常量区，并带中文注释。
4. 输出结果按用户要求结合申万行业信息时，join dim_sw_industry 取 is_latest=1 的归属。
5. 不要假设存在上述之外的表或字段。"""
        if with_backtest:
            system_prompt += '\n' + BACKTEST_REQUIREMENT

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'选股/量化条件：\n{requirement}'},
        ]

        raw = self.llm_client.chat(messages, temperature=0.2, max_tokens=4096)

        # 提取 ```python 代码块；模型未按格式输出时回退为原始文本
        code = raw
        match = re.search(r'```(?:python)?\s*\n([\s\S]*?)```', raw)
        if match:
            code = match.group(1).strip()

        return True, '生成成功', {'code': code, 'model': self.llm_client.model}
