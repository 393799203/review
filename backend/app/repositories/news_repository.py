#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from datetime import datetime
from sqlalchemy import desc
from models import ClsNews
from app.repositories.base_repository import BaseRepository


class NewsRepository(BaseRepository):
    """新闻仓库类"""
    
    def __init__(self):
        super().__init__(ClsNews)
    
    def get_total_count(self) -> int:
        """获取新闻总数"""
        session = self.create_session()
        try:
            return session.query(ClsNews).count()
        finally:
            session.close()
    
    def get_news_list(self, limit: int = 50, last_ctime: datetime = None, keyword: str = None) -> List[ClsNews]:
        """获取新闻列表"""
        session = self.create_session()
        try:
            query = session.query(ClsNews)
            
            if keyword:
                search_pattern = f"%{keyword}%"
                query = query.filter(
                    (ClsNews.title.ilike(search_pattern)) | 
                    (ClsNews.content.ilike(search_pattern))
                )
            
            if last_ctime:
                query = query.filter(ClsNews.ctime < last_ctime)
            
            query = query.order_by(ClsNews.ctime.desc())
            
            return query.limit(limit).all()
        finally:
            session.close()
    
    def get_by_news_id(self, news_id: str) -> Optional[ClsNews]:
        """根据新闻ID获取新闻"""
        session = self.create_session()
        try:
            return session.query(ClsNews).filter(ClsNews.news_id == news_id).first()
        finally:
            session.close()
    
    def get_by_ctime(self, ctime: datetime) -> Optional[ClsNews]:
        """根据时间获取新闻"""
        session = self.create_session()
        try:
            return session.query(ClsNews).filter(ClsNews.ctime == ctime).first()
        finally:
            session.close()
    
    def bulk_update_or_create(self, news_data_list: List[dict]) -> int:
        """批量更新或创建新闻"""
        session = self.create_session()
        try:
            news_ids = [str(item.get('id')) for item in news_data_list if item.get('title') or item.get('content')]
            
            existing_news = session.query(ClsNews).filter(ClsNews.news_id.in_(news_ids)).all()
            existing_dict = {news.news_id: news for news in existing_news}
            
            saved_count = 0
            for item in news_data_list:
                title = item.get('title', '')
                content = item.get('content', '')
                
                if not title and not content:
                    continue
                
                import re
                import json
                
                stock_list = item.get('stock_list', [])
                confirmed = item.get('confirmed', 0)
                reading_num = item.get('reading_num', 0)
                has_stocks = len(stock_list) > 0
                recommend = item.get('recommend', 0)
                is_important = recommend == 1
                clean_content = re.sub(r'【[^】]*】', '', content)
                
                ctime_timestamp = item.get('ctime', 0)
                ctime_dt = datetime.fromtimestamp(ctime_timestamp)
                news_id = str(item.get('id'))
                
                existing = existing_dict.get(news_id)
                
                if existing:
                    existing.title = title
                    existing.content = clean_content
                    existing.is_important = 1 if is_important else 0
                    existing.has_stocks = 1 if has_stocks else 0
                    existing.confirmed = 1 if confirmed == 1 else 0
                    existing.reading_num = reading_num
                    existing.stock_list = json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                else:
                    news_record = ClsNews(
                        news_id=news_id,
                        title=title,
                        content=clean_content,
                        ctime=ctime_dt,
                        is_important=1 if is_important else 0,
                        has_stocks=1 if has_stocks else 0,
                        confirmed=1 if confirmed == 1 else 0,
                        reading_num=reading_num,
                        stock_list=json.dumps([{'code': s.get('StockID', ''), 'name': s.get('name', '')} for s in stock_list]) if has_stocks else None
                    )
                    session.add(news_record)
                    saved_count += 1
            
            session.commit()
            return saved_count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
