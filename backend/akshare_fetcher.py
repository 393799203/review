#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akshare数据获取器
"""

import akshare as ak
import pandas as pd
from typing import Dict, Optional
import time
import requests
import re


class AkshareFetcher:
    """Akshare数据获取器"""
    
    def __init__(self):
        self.timeout = 120  # akshare接口较慢，设置较长超时时间
    
    def get_limit_up_pool(self, date_str: str) -> Optional[pd.DataFrame]:
        """
        获取涨停股票池数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            涨停股票池DataFrame
        """
        try:
            print(f"从akshare获取涨停股票池数据...")
            start_time = time.time()
            
            df = ak.stock_zt_pool_em(date=date_str)
            
            elapsed_time = time.time() - start_time
            count = len(df) if df is not None and not df.empty else 0
            print(f"✓ akshare涨停股票池获取到 {count} 只股票，耗时 {elapsed_time:.2f} 秒")
            
            return df
        except Exception as e:
            print(f"✗ 获取akshare涨停股票池失败: {e}")
            return None
    
    def get_strong_pool(self, date_str: str) -> Optional[pd.DataFrame]:
        """
        获取强势股数据（包含涨停原因）
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            强势股DataFrame
        """
        try:
            print(f"从akshare获取强势股数据...")
            start_time = time.time()
            
            df = ak.stock_zt_pool_strong_em(date=date_str)
            
            elapsed_time = time.time() - start_time
            count = len(df) if df is not None and not df.empty else 0
            print(f"✓ akshare强势股获取到 {count} 只股票，耗时 {elapsed_time:.2f} 秒")
            
            return df
        except Exception as e:
            print(f"✗ 获取akshare强势股失败: {e}")
            return None
    
    def get_continuous_pool(self, date_str: str) -> Optional[pd.DataFrame]:
        """
        获取连板股数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            连板股DataFrame
        """
        try:
            print(f"从akshare获取连板股数据...")
            start_time = time.time()
            
            df = ak.stock_zt_pool_zbgc_em(date=date_str)
            
            elapsed_time = time.time() - start_time
            count = len(df) if df is not None and not df.empty else 0
            print(f"✓ akshare连板股获取到 {count} 只股票，耗时 {elapsed_time:.2f} 秒")
            
            return df
        except Exception as e:
            print(f"✗ 获取akshare连板股失败: {e}")
            return None
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict]:
        """
        获取单只股票的实时行情（通过新浪财经API，速度快）
        
        Args:
            stock_code: 股票代码（6位数字）
            
        Returns:
            实时行情数据字典
        """
        try:
            print(f"从新浪财经API获取股票 {stock_code} 的实时行情...")
            start_time = time.time()
            
            if stock_code.startswith('6'):
                symbol = f"sh{stock_code}"
            else:
                symbol = f"sz{stock_code}"
            
            url = f"http://hq.sinajs.cn/list={symbol}"
            
            headers = {
                'Referer': 'http://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.encoding = 'gbk'
            
            pattern = re.compile(r'="(.*)"')
            match = pattern.search(response.text)
            
            elapsed_time = time.time() - start_time
            
            if match:
                data_str = match.group(1)
                data_list = data_str.split(',')
                
                if len(data_list) >= 32:
                    price = float(data_list[3]) if data_list[3] else None
                    prev_close = float(data_list[2]) if data_list[2] else None
                    
                    result = {
                        'code': stock_code,
                        'name': data_list[0],
                        'open': float(data_list[1]) if data_list[1] else None,
                        'prev_close': prev_close,
                        'price': price,
                        'high': float(data_list[4]) if data_list[4] else None,
                        'low': float(data_list[5]) if data_list[5] else None,
                        'volume': float(data_list[8]) if data_list[8] else 0,
                        'amount': float(data_list[9]) if data_list[9] else 0,
                        'change_amount': price - prev_close if price and prev_close else 0,
                        'change_percent': ((price - prev_close) / prev_close * 100) if price and prev_close else 0,
                    }
                    print(f"✓ 新浪财经API获取股票 {stock_code} 实时行情成功，耗时 {elapsed_time:.2f} 秒")
                    return result
            
            print(f"✗ 未找到股票 {stock_code} 的数据")
            return None
            
        except Exception as e:
            print(f"✗ 获取实时行情失败: {e}")
            return None
    
    def get_all_data(self, date_str: str) -> Dict:
        """
        获取所有akshare数据
        
        Args:
            date_str: 日期字符串（YYYYMMDD）
            
        Returns:
            包含所有数据的字典
        """
        print(f"\n从akshare获取 {date_str} 的数据...")
        
        return {
            'limit_up_pool': self.get_limit_up_pool(date_str),
            'strong_pool': self.get_strong_pool(date_str),
            'continuous_pool': self.get_continuous_pool(date_str),
        }
