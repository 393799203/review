#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
from datetime import datetime, date
from models import StockDiffRecord
from app.repositories.base_repository import BaseRepository
from database import get_db_session


class StockDiffRepository(BaseRepository):
    """股票对比仓库类"""
    
    def __init__(self):
        super().__init__(StockDiffRecord)
    
    def delete_by_date(self, trade_date: date) -> bool:
        """删除指定日期的所有记录"""
        session = get_db_session()
        try:
            session.query(StockDiffRecord).filter(
                StockDiffRecord.trade_date == trade_date
            ).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def bulk_save_records(self, records: List[StockDiffRecord]) -> bool:
        """批量保存记录"""
        session = get_db_session()
        try:
            session.bulk_save_objects(records)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_by_date(self, trade_date: date) -> List[StockDiffRecord]:
        """获取指定日期的所有记录"""
        session = get_db_session()
        try:
            return session.query(StockDiffRecord).filter(
                StockDiffRecord.trade_date == trade_date
            ).all()
        finally:
            session.close()
