#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akshare数据获取器
"""

import akshare as ak
import pandas as pd
from typing import Dict, Optional
import time


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
