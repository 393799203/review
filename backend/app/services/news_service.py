#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import json
import re
import time
import requests as req_module
from app.services.base_service import BaseService
from app.repositories.news_repository import NewsRepository
from models import ClsNews


class NewsService(BaseService):
    """新闻服务类"""
    
    def __init__(self):
        super().__init__(NewsRepository())
        self.news_repository = self.repository
    
    def get_cls_telegraph(self, force: bool = False, last_ctime: str = None,
                         limit: int = 50, load_from_api: bool = False,
                         keyword: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取财联社电报数据
        
        Args:
            force: 是否强制从财联社刷新
            last_ctime: 最后一条新闻的时间
            limit: 每次加载数量
            load_from_api: 是否从API加载历史数据
            keyword: 搜索关键词
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            total_count = self.news_repository.get_total_count()
            
            if keyword:
                return self._search_news(keyword, limit)
            
            if not force and not load_from_api:
                return self._get_from_cache(last_ctime, limit, total_count)
            
            return self._fetch_from_api(last_ctime, limit, load_from_api, total_count)
            
        except Exception as e:
            return False, str(e), None
    
    def _search_news(self, keyword: str, limit: int) -> Tuple[bool, str, Dict]:
        """搜索新闻"""
        db_news = self.news_repository.get_news_list(limit=limit, keyword=keyword)
        
        news_list = []
        for item in db_news:
            stock_list = []
            if item.stock_list:
                try:
                    stock_list = json.loads(item.stock_list)
                except:
                    pass
            
            news_list.append({
                'id': item.news_id,
                'title': item.title or '',
                'content': item.content or '',
                'ctime': item.ctime.strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'C',
                'is_important': item.is_important == 1,
                'level_text': '加红' if item.is_important == 1 else '普通',
                'has_stocks': item.has_stocks == 1,
                'confirmed': item.confirmed == 1,
                'reading_num': item.reading_num or 0,
                'stock_list': stock_list
            })
        
        return True, '搜索成功', {
            'data': news_list,
            'from_cache': True,
            'has_more': False,
            'total': len(news_list),
            'keyword': keyword
        }
    
    def _get_from_cache(self, last_ctime: str, limit: int, total_count: int) -> Tuple[bool, str, Dict]:
        """从缓存获取新闻"""
        last_ctime_dt = None
        if last_ctime:
            try:
                last_ctime_dt = datetime.strptime(last_ctime, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        
        db_news = self.news_repository.get_news_list(limit=limit, last_ctime=last_ctime_dt)
        
        if db_news:
            news_list = self._format_news_list(db_news)
            has_more = len(db_news) >= limit
            
            return True, '获取成功', {
                'data': news_list,
                'from_cache': True,
                'has_more': has_more,
                'total': total_count
            }
        else:
            return True, '获取成功', {
                'data': [],
                'from_cache': True,
                'has_more': False,
                'total': total_count
            }
    
    def _fetch_from_api(self, last_ctime: str, limit: int, 
                        load_from_api: bool, total_count: int) -> Tuple[bool, str, Dict]:
        """从API获取新闻"""
        url = "https://www.cls.cn/nodeapi/telegraphList"
        params = {
            "app": "CailianpressWeb",
            "os": "web",
            "refresh_type": "2" if last_ctime and load_from_api else "1",
            "order": "1",
            "rn": "50",
            "sv": "8.4.6"
        }
        
        if last_ctime and load_from_api:
            try:
                last_ctime_dt = datetime.strptime(last_ctime, '%Y-%m-%d %H:%M:%S')
                last_news = self.news_repository.get_by_ctime(last_ctime_dt)
                
                if last_news:
                    params["last_id"] = last_news.news_id
            except ValueError:
                pass
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cls.cn/telegraph"
        }
        
        response = req_module.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return False, f'请求失败: {response.status_code}', None
        
        data = response.json()
        roll_data = data.get('data', {}).get('roll_data', [])
        
        saved_count = self.news_repository.bulk_update_or_create(roll_data)
        
        news_list = []
        for item in roll_data:
            title = item.get('title', '')
            content = item.get('content', '')
            
            if not title and not content:
                continue
            
            stock_list = item.get('stock_list', [])
            has_stocks = len(stock_list) > 0
            recommend = item.get('recommend', 0)
            is_important = recommend == 1
            confirmed = item.get('confirmed', 0)
            reading_num = item.get('reading_num', 0)
            
            ctime_timestamp = item.get('ctime', 0)
            local_time = time.localtime(ctime_timestamp)
            
            news_list.append({
                'id': str(item.get('id')),
                'title': title,
                'content': re.sub(r'【[^】]*】', '', content),
                'ctime': time.strftime("%Y-%m-%d %H:%M:%S", local_time),
                'level': item.get('level', 'C'),
                'is_important': is_important,
                'level_text': '加红' if is_important else '普通',
                'has_stocks': has_stocks,
                'confirmed': confirmed == 1,
                'reading_num': reading_num,
                'stock_list': [{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list] if has_stocks else []
            })
        
        news_list.sort(key=lambda x: x['ctime'], reverse=True)
        
        return True, '获取成功', {
            'data': news_list,
            'saved_count': saved_count,
            'from_cache': False,
            'has_more': len(news_list) >= limit
        }
    
    def _format_news_list(self, db_news: List[ClsNews]) -> List[Dict]:
        """格式化新闻列表"""
        news_list = []
        for item in db_news:
            stock_list = []
            if item.stock_list:
                try:
                    stock_list = json.loads(item.stock_list)
                except:
                    pass
            
            news_list.append({
                'id': item.news_id,
                'title': item.title or '',
                'content': item.content or '',
                'ctime': item.ctime.strftime("%Y-%m-%d %H:%M:%S"),
                'level': 'C',
                'is_important': item.is_important == 1,
                'level_text': '加红' if item.is_important == 1 else '普通',
                'has_stocks': item.has_stocks == 1,
                'confirmed': item.confirmed == 1,
                'reading_num': item.reading_num or 0,
                'stock_list': stock_list
            })
        
        return news_list
