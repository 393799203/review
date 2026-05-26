#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.report_service import ReportService


class ReportController(BaseController):
    """研报控制器类"""
    
    def __init__(self):
        super().__init__(ReportService())
        self.report_service = self.service
    
    def get_reports(self):
        """获取研报列表"""
        try:
            page = int(self.get_query_param('page', 1))
            page_size = int(self.get_query_param('pageSize', 50))
            stock_code = self.get_query_param('code', '')
            
            success, message, data = self.report_service.get_reports(
                page, page_size, stock_code
            )
            
            if success:
                return self.success(data=data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)


report_controller = ReportController()
