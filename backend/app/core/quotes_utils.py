#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情数据获取工具
"""

from typing import List, Dict, Optional
from decimal import Decimal


def get_realtime_quotes(stock_codes: List[str], debug: bool = False) -> Dict[str, Dict]:
    """
    批量获取股票实时行情
    
    Args:
        stock_codes: 股票代码列表
        debug: 是否打印调试信息
        
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
    
    for stock in stocks:
        quote = quotes_dict.get(stock.stock_code)
        if quote and quote['prev_close'] > 0:
            # next_change: 当前价格相对昨收的涨跌幅（收盘后即为收盘涨跌幅）
            change_percent = calculate_change_percent(quote['price'], quote['prev_close'])
            if change_percent is not None:
                stock.next_change = Decimal(str(round(change_percent, 4)))
            
            # next_open_change: 开盘价相对昨收的涨跌幅（竞价溢价）
            if quote.get('open', 0) > 0:
                open_change = calculate_change_percent(quote['open'], quote['prev_close'])
                if open_change is not None:
                    stock.next_open_change = Decimal(str(round(open_change, 4)))
            
            updated_count += 1
    
    if debug:
        print(f"✓ 更新了 {updated_count} 只股票的次日涨跌幅和竞价溢价")
    
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
