#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from datetime import datetime, date
from sqlalchemy import desc
from models import AIAnalysisResult, WatchlistAnalysisResult, ResearchReportAnalysisResult, LimitUpStock, ClsNews
from app.repositories.base_repository import BaseRepository


class AIRepository(BaseRepository):
    """AI分析仓库类"""
    
    def __init__(self):
        super().__init__(AIAnalysisResult)
    
    def get_limit_up_stock_by_code(self, stock_code: str, trade_date: date = None) -> Optional[LimitUpStock]:
        """获取涨停股票信息"""
        from database import get_db_session
        session = get_db_session()
        try:
            if trade_date:
                return session.query(LimitUpStock).filter(
                    LimitUpStock.stock_code == stock_code,
                    LimitUpStock.trade_date == trade_date
                ).first()
            else:
                return session.query(LimitUpStock).filter(
                    LimitUpStock.stock_code == stock_code
                ).order_by(desc(LimitUpStock.trade_date)).first()
        finally:
            session.close()
    
    def get_ai_analysis_cache(self, stock_code: str, trade_date: date) -> Optional[AIAnalysisResult]:
        """获取AI分析缓存"""
        from database import get_db_session
        session = get_db_session()
        try:
            return session.query(AIAnalysisResult).filter(
                AIAnalysisResult.stock_code == stock_code,
                AIAnalysisResult.trade_date == trade_date
            ).first()
        finally:
            session.close()
    
    def save_ai_analysis(self, stock_code: str, stock_name: str, 
                        trade_date: date, analysis_result: dict) -> bool:
        """保存AI分析结果"""
        import json
        from database import get_db_session
        session = get_db_session()
        try:
            cached_result = session.query(AIAnalysisResult).filter(
                AIAnalysisResult.stock_code == stock_code,
                AIAnalysisResult.trade_date == trade_date
            ).first()
            
            if cached_result:
                cached_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                cached_result.updated_at = datetime.now()
            else:
                new_result = AIAnalysisResult(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    trade_date=trade_date,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False)
                )
                session.add(new_result)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_news_by_id(self, news_id: str) -> Optional[ClsNews]:
        """根据ID获取新闻"""
        from database import get_db_session
        session = get_db_session()
        try:
            return session.query(ClsNews).filter(ClsNews.news_id == str(news_id)).first()
        finally:
            session.close()
    
    def update_news_analysis(self, news_id: str, analysis_result: dict) -> bool:
        """更新新闻分析结果"""
        import json
        from database import get_db_session
        session = get_db_session()
        try:
            news_record = session.query(ClsNews).filter(ClsNews.news_id == str(news_id)).first()
            if news_record:
                news_record.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                news_record.analyzed_at = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_watchlist_analysis_cache(self, stock_code: str, analysis_date: date) -> Optional[WatchlistAnalysisResult]:
        """获取自选股分析缓存"""
        from database import get_db_session
        session = get_db_session()
        try:
            return session.query(WatchlistAnalysisResult).filter(
                WatchlistAnalysisResult.stock_code == stock_code,
                WatchlistAnalysisResult.analysis_date == analysis_date
            ).first()
        finally:
            session.close()
    
    def save_watchlist_analysis(self, stock_code: str, stock_name: str,
                                analysis_date: date, analysis_result: dict) -> bool:
        """保存自选股分析结果"""
        import json
        from database import get_db_session
        session = get_db_session()
        try:
            existing_result = session.query(WatchlistAnalysisResult).filter(
                WatchlistAnalysisResult.stock_code == stock_code,
                WatchlistAnalysisResult.analysis_date == analysis_date
            ).first()
            
            if existing_result:
                existing_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                existing_result.updated_at = datetime.now()
            else:
                new_result = WatchlistAnalysisResult(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    analysis_date=analysis_date,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False)
                )
                session.add(new_result)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_report_analysis_cache(self, info_code: str) -> Optional[ResearchReportAnalysisResult]:
        """获取研报分析缓存"""
        from database import get_db_session
        session = get_db_session()
        try:
            return session.query(ResearchReportAnalysisResult).filter(
                ResearchReportAnalysisResult.info_code == info_code
            ).first()
        finally:
            session.close()
    
    def save_report_analysis(self, info_code: str, stock_code: str, stock_name: str,
                            title: str, rating: str, rating_change: str,
                            analysis_date: date, analysis_result: dict) -> bool:
        """保存研报分析结果"""
        import json
        from database import get_db_session
        session = get_db_session()
        try:
            existing_result = session.query(ResearchReportAnalysisResult).filter(
                ResearchReportAnalysisResult.info_code == info_code
            ).first()
            
            if existing_result:
                existing_result.analysis_result = json.dumps(analysis_result, ensure_ascii=False)
                existing_result.rating = rating
                existing_result.rating_change = rating_change
                existing_result.updated_at = datetime.now()
            else:
                new_result = ResearchReportAnalysisResult(
                    info_code=info_code,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    title=title,
                    rating=rating,
                    rating_change=rating_change,
                    analysis_result=json.dumps(analysis_result, ensure_ascii=False),
                    analysis_date=analysis_date
                )
                session.add(new_result)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
