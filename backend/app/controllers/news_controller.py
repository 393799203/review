#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.news_service import NewsService


class NewsController(BaseController):
    """新闻控制器类"""
    
    def __init__(self):
        super().__init__(NewsService())
        self.news_service = self.service
    
    def get_cls_telegraph(self):
        """获取财联社电报数据"""
        try:
            force = self.get_query_param('force', 'false').lower() == 'true'
            last_ctime = self.get_query_param('last_ctime')
            limit = int(self.get_query_param('limit', 50))
            load_from_api = self.get_query_param('load_from_api', 'false').lower() == 'true'
            keyword = self.get_query_param('keyword', '').strip()
            
            success, message, data = self.news_service.get_cls_telegraph(
                force, last_ctime, limit, load_from_api, keyword
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)


news_controller = NewsController()
