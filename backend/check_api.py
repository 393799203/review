#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 stock_individual_info_em 接口返回的数据格式
"""

import akshare as ak

print("测试 stock_individual_info_em 接口")
print("="*60)

stock_code = '600519'
print(f"\n获取股票 {stock_code} 的信息...")
info = ak.stock_individual_info_em(symbol=stock_code)

print("\n返回的数据类型:", type(info))
print("\n返回的数据:\n", info)

if info is not None and not info.empty:
    print("\n数据列名:", info.columns.tolist())
    print("\n数据形状:", info.shape)
    
    print("\n转换为字典:")
    info_dict = dict(zip(info['item'], info['value']))
    for key, value in info_dict.items():
        print(f"  {key}: {value}")
