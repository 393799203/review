#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple
from app.services.base_service import BaseService
from app.repositories.report_repository import ReportRepository
from core.data_fetcher import DataFetcher


class ReportService(BaseService):
    """研报服务类"""
    
    def __init__(self):
        super().__init__(ReportRepository())
        self.report_repository = self.repository
        self.data_fetcher = DataFetcher()
    
    def get_reports(self, page: int = 1, page_size: int = 50,
                   stock_code: str = '') -> Tuple[bool, str, Optional[Dict]]:
        """
        获取研报列表
        
        Args:
            page: 页码
            page_size: 每页数量
            stock_code: 股票代码
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if stock_code:
                stock_code = self.data_fetcher.get_stock_code_by_name(stock_code)
            
            result = self.report_repository.get_reports(page, page_size, stock_code)
            
            if result:
                return True, '获取成功', result
            else:
                return False, '获取研报数据失败', None
                
        except Exception as e:
            return False, str(e), None
