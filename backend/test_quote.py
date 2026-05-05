#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试股票实时行情获取功能
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ths_fetcher import ThsFetcher
from akshare_fetcher import AkshareFetcher

def test_realtime_quote():
    """测试实时行情获取"""
    
    print("="*60)
    print("测试股票实时行情获取功能")
    print("="*60)
    
    test_stocks = [
        '600519',  # 贵州茅台
        '000001',  # 平安银行
        '300750',  # 宁德时代
    ]
    
    print("\n方法1：使用 ThsFetcher 获取实时行情")
    print("-"*60)
    ths_fetcher = ThsFetcher()
    
    for stock_code in test_stocks:
        print(f"\n获取股票 {stock_code} 的实时行情...")
        quote = ths_fetcher.get_realtime_quote(stock_code)
        
        if quote:
            print(f"✓ 成功获取 {quote['name']} ({quote['code']}) 的行情")
            print(f"  最新价: {quote['price']}")
            print(f"  涨跌幅: {quote['change_percent']:.2f}%")
            print(f"  成交量: {quote['volume']:.0f}手")
            print(f"  成交额: {quote['amount']:.0f}万元")
        else:
            print(f"✗ 获取失败")
    
    print("\n" + "="*60)
    print("\n方法2：使用 AkshareFetcher 获取实时行情")
    print("-"*60)
    akshare_fetcher = AkshareFetcher()
    
    for stock_code in test_stocks:
        print(f"\n获取股票 {stock_code} 的实时行情...")
        quote = akshare_fetcher.get_realtime_quote(stock_code)
        
        if quote:
            print(f"✓ 成功获取 {quote['name']} ({quote['code']}) 的行情")
            print(f"  最新价: {quote['price']}")
            print(f"  涨跌幅: {quote['change_percent']:.2f}%")
            print(f"  成交量: {quote['volume']:.0f}手")
            print(f"  成交额: {quote['amount']:.0f}万元")
        else:
            print(f"✗ 获取失败")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == '__main__':
    test_realtime_quote()
