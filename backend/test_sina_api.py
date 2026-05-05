#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用新浪财经API获取实时行情（推荐方案）
"""

import requests
import re

def get_realtime_quote_sina(stock_code: str) -> dict:
    """
    通过新浪财经API获取单只股票实时行情（快速方法）
    
    Args:
        stock_code: 股票代码（6位数字）
        
    Returns:
        实时行情数据字典
    """
    try:
        # 根据股票代码判断市场
        if stock_code.startswith('6'):
            symbol = f"sh{stock_code}"
        else:
            symbol = f"sz{stock_code}"
        
        # 新浪财经API
        url = f"http://hq.sinajs.cn/list={symbol}"
        
        headers = {
            'Referer': 'http://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'
        
        # 解析数据
        pattern = re.compile(r'="(.*)"')
        match = pattern.search(response.text)
        
        if match:
            data_str = match.group(1)
            data_list = data_str.split(',')
            
            if len(data_list) >= 32:
                return {
                    'code': stock_code,
                    'name': data_list[0],
                    'open': float(data_list[1]) if data_list[1] else None,
                    'prev_close': float(data_list[2]) if data_list[2] else None,
                    'price': float(data_list[3]) if data_list[3] else None,
                    'high': float(data_list[4]) if data_list[4] else None,
                    'low': float(data_list[5]) if data_list[5] else None,
                    'volume': float(data_list[8]) if data_list[8] else 0,
                    'amount': float(data_list[9]) if data_list[9] else 0,
                    'change_amount': float(data_list[3]) - float(data_list[2]) if data_list[2] and data_list[3] else 0,
                    'change_percent': ((float(data_list[3]) - float(data_list[2])) / float(data_list[2]) * 100) if data_list[2] and data_list[3] else 0,
                }
        
        return None
        
    except Exception as e:
        print(f"✗ 新浪财经API获取失败: {e}")
        return None


if __name__ == '__main__':
    print("测试新浪财经API获取实时行情")
    print("="*60)
    
    test_stocks = ['600519', '000001', '300750']
    
    for stock_code in test_stocks:
        print(f"\n获取股票 {stock_code} 的实时行情...")
        quote = get_realtime_quote_sina(stock_code)
        
        if quote:
            print(f"✓ 成功获取 {quote['name']} ({quote['code']}) 的行情")
            print(f"  最新价: {quote['price']}")
            print(f"  涨跌幅: {quote['change_percent']:.2f}%")
            print(f"  涨跌额: {quote['change_amount']:.2f}")
            print(f"  成交量: {quote['volume']:.0f}手")
            print(f"  成交额: {quote['amount']:.0f}万元")
        else:
            print(f"✗ 获取失败")
