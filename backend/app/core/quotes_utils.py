#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情数据获取工具
"""

import re
import urllib.request
from typing import List, Dict, Optional
from decimal import Decimal

SINA_QUOTE_URL = "https://hq.sinajs.cn/list={symbols}"
_SINA_CTX = None


def _sina_ssl_ctx():
    """新浪 hq.sinajs.cn 证书链在本机常缺根证书,按需绕过校验(仅读行情)"""
    global _SINA_CTX
    if _SINA_CTX is None:
        import ssl
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        _SINA_CTX = ctx
    return _SINA_CTX


def _sina_symbol(code: str) -> str:
    """股票代码 → 新浪格式(沪: sh600519, 深: sz000001)"""
    code = str(code).strip().lower()
    if code.startswith(('sh', 'sz', 'bj')):
        return code
    if code.startswith('6'):
        return 'sh' + code
    if code.startswith(('0', '3')):
        return 'sz' + code
    if code.startswith(('4', '8')):
        return 'bj' + code
    return 'sh' + code


def _parse_sina_line(line: str) -> Optional[Dict]:
    """解析新浪行情行: var hq_str_sh600519="名称,今开,昨收,现价,最高,最低,...";"""
    m = re.match(r'var hq_str_(\w+)="([^"]*)";', line.strip())
    if not m:
        return None
    symbol = m.group(1)
    fields = m.group(2).split(',')
    if len(fields) < 32 or not fields[0]:
        return None  # 停牌/无效代码返回空串

    def f(idx: int) -> float:
        try:
            return float(fields[idx] or 0)
        except (ValueError, IndexError):
            return 0.0

    def bid_ask(base: int) -> Dict[str, float]:
        """五档: fields[10..19] 买五档(价,量), fields[20..29] 卖五档"""
        out = {}
        for i in range(5):
            out[f'bid{i+1}'] = f(base + i * 2)
            out[f'bid_vol{i+1}'] = f(base + i * 2 + 1)
            out[f'ask{i+1}'] = f(base + 10 + i * 2)
            out[f'ask_vol{i+1}'] = f(base + 10 + i * 2 + 1)
        return out

    code = symbol[2:]
    price = f(3)
    prev_close = f(2)
    if price <= 0:  # 竞价时段现价为 0,用买一价兜底(与 mootdx 分支一致)
        bid1 = f(10)
        price = bid1 if bid1 > 0 else prev_close

    quote = {
        'code': code,
        'name': fields[0],
        'open': f(1),
        'prev_close': prev_close,
        'price': price,
        'high': f(4),
        'low': f(5),
        'volume': f(8),
        'amount': f(9),
    }
    quote.update(bid_ask(10))
    return quote


def get_realtime_quotes_from_sina(stock_codes: List[str], debug: bool = False) -> Dict[str, Dict]:
    """通过新浪 HTTP 行情接口批量获取实时行情(通达信 quotes 协议失效时的兜底)。

    Returns:
        股票行情字典,格式: {股票代码: {'price': 价格, 'prev_close': 昨收, 'open': 开盘价, ...}}
    """
    if not stock_codes:
        return {}
    symbols = ','.join(_sina_symbol(c) for c in stock_codes)
    req = urllib.request.Request(
        SINA_QUOTE_URL.format(symbols=symbols),
        headers={
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0 (compatible; DeqingStock/1.0)',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=_sina_ssl_ctx()) as resp:
            raw = resp.read().decode('gbk', errors='ignore')
    except Exception as e:
        if debug:
            print(f"新浪行情请求失败: {e}")
        return {}

    quotes_dict = {}
    for line in raw.strip().splitlines():
        q = _parse_sina_line(line)
        if q:
            quotes_dict[q['code']] = q
    if debug:
        print(f"新浪行情返回 {len(quotes_dict)} 只")
    return quotes_dict


def get_realtime_quotes(stock_codes: List[str], debug: bool = False,
                        use_sina_fallback: bool = True) -> Dict[str, Dict]:
    """
    批量获取股票实时行情

    Args:
        stock_codes: 股票代码列表
        debug: 是否打印调试信息
        use_sina_fallback: mootdx(通达信) 返回为空时,是否回退新浪 HTTP 行情

    Returns:
        股票行情字典，格式：{股票代码: {'price': 价格, 'prev_close': 昨收, 'open': 开盘价}}
    """
    if not stock_codes:
        return {}
    
    sh_codes = [code for code in stock_codes if code.startswith('6')]
    sz_codes = [code for code in stock_codes if code.startswith(('0', '3'))]
    
    if debug:
        print(f"沪市股票: {len(sh_codes)} 只, 深市股票: {len(sz_codes)} 只")
    
    quotes_dict = {}
    
    if sh_codes:
        try:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market=1)
            quotes = client.quotes(symbol=sh_codes)
            
            if debug:
                print(f"沪市行情返回: {quotes is not None and hasattr(quotes, 'empty') and not quotes.empty}")
            
            if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                for idx, row in quotes.iterrows():
                    code = row['code']
                    quotes_dict[code] = {
                        'price': float(row.get('price', 0) or 0),
                        'prev_close': float(row.get('last_close', 0) or 0),
                        'open': float(row.get('open', 0) or 0),
                    }
                if debug:
                    print(f"成功获取沪市行情: {len([k for k in quotes_dict.keys() if k.startswith('6')])} 只")
        except Exception as e:
            if debug:
                print(f"批量获取沪市实时行情失败: {e}")
    
    if sz_codes:
        try:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market=0)
            quotes = client.quotes(symbol=sz_codes)
            
            if debug:
                print(f"深市行情返回: {quotes is not None and hasattr(quotes, 'empty') and not quotes.empty}")
            
            if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                for idx, row in quotes.iterrows():
                    code = row['code']
                    quotes_dict[code] = {
                        'price': float(row.get('price', 0) or 0),
                        'prev_close': float(row.get('last_close', 0) or 0),
                        'open': float(row.get('open', 0) or 0),
                    }
                if debug:
                    print(f"成功获取深市行情: {len([k for k in quotes_dict.keys() if k.startswith(('0', '3'))])} 只")
        except Exception as e:
            if debug:
                print(f"批量获取深市实时行情失败: {e}")
    
    # mootdx(通达信 quotes) 为空 → 回退新浪 HTTP 行情(通达信服务器已拒绝旧 quotes 命令)
    if use_sina_fallback and len(quotes_dict) < len(stock_codes):
        missing = [c for c in stock_codes if c not in quotes_dict]
        sina = get_realtime_quotes_from_sina(missing, debug=debug)
        for code, q in sina.items():
            quotes_dict[code] = {
                'price': q['price'],
                'prev_close': q['prev_close'],
                'open': q['open'],
            }
    
    return quotes_dict


def calculate_change_percent(current_price: float, prev_close: float) -> Optional[float]:
    """
    计算涨跌幅
    
    Args:
        current_price: 当前价格
        prev_close: 昨日收盘价
        
    Returns:
        涨跌幅（百分比），如果无法计算返回None
    """
    if prev_close <= 0 or current_price <= 0:
        return None
    
    return (current_price - prev_close) / prev_close * 100


def update_stocks_next_change(stocks: List, quotes_dict: Dict[str, Dict], debug: bool = False) -> int:
    """
    批量更新股票的next_change和next_open_change字段
    
    Args:
        stocks: 股票对象列表（LimitUpStock对象）
        quotes_dict: 股票行情字典
        debug: 是否打印调试信息
        
    Returns:
        更新的股票数量
    """
    updated_count = 0
    open_change_count = 0
    
    for stock in stocks:
        quote = quotes_dict.get(stock.stock_code)
        if quote and quote['prev_close'] > 0:
            # next_change: 当前价格相对昨收的涨跌幅（收盘后即为收盘涨跌幅）
            change_percent = calculate_change_percent(quote['price'], quote['prev_close'])
            if change_percent is not None:
                stock.next_change = Decimal(str(round(change_percent, 4)))
            
            # next_open_change: 开盘价相对昨收的涨跌幅（竞价溢价）
            open_price = quote.get('open', 0)
            if open_price > 0:
                open_change = calculate_change_percent(open_price, quote['prev_close'])
                if open_change is not None:
                    stock.next_open_change = Decimal(str(round(open_change, 4)))
                    open_change_count += 1
            else:
                if debug:
                    print(f"⚠ {stock.stock_name}({stock.stock_code}) 开盘价为0或None，无法计算竞价溢价")
            
            updated_count += 1
    
    if debug:
        print(f"✓ 更新了 {updated_count} 只股票的次日涨跌幅")
        print(f"✓ 更新了 {open_change_count} 只股票的竞价溢价（共{updated_count}只）")
    
    return updated_count


def update_stock_data_change_percent(stock_data_list: List[Dict], quotes_dict: Dict[str, Dict]) -> int:
    """
    批量更新股票数据的change_percent字段
    
    Args:
        stock_data_list: 股票数据列表（字典列表）
        quotes_dict: 股票行情字典
        
    Returns:
        更新的股票数量
    """
    updated_count = 0
    
    for stock_data in stock_data_list:
        quote = quotes_dict.get(stock_data['code'])
        if quote and quote['prev_close'] > 0:
            change_percent = calculate_change_percent(quote['price'], quote['prev_close'])
            if change_percent is not None:
                stock_data['change_percent'] = change_percent
                updated_count += 1
    
    return updated_count
