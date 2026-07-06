#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, List
from app.repositories.base_repository import BaseRepository
from models import ResearchReportAnalysisResult
from app.core.data_fetcher import DataFetcher


class ReportRepository(BaseRepository):
    """研报仓库类"""
    
    def __init__(self):
        super().__init__(None)
        self.data_fetcher = DataFetcher()
    
    def get_reports(self, page: int = 1, page_size: int = 50, 
                   stock_code: str = '') -> Optional[Dict]:
        """
        获取研报列表
        
        Args:
            page: 页码
            page_size: 每页数量
            stock_code: 股票代码
            
        Returns:
            研报数据
        """
        return self.data_fetcher.get_reports(page, page_size, stock_code)
