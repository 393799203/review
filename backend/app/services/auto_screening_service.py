#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日自动筛选配置服务"""

import json
from typing import Dict, Optional, Tuple

from app.services.base_service import BaseService
from app.repositories.base_repository import BaseRepository
from models import AutoScreeningConfig, AutoScreeningLog
from app.repositories.user_repository import UserRepository


class AutoScreeningRepository(BaseRepository):
    """每日自动筛选仓库"""

    def __init__(self):
        super().__init__(AutoScreeningConfig)

    def get_config(self, user_id: str) -> Optional[AutoScreeningConfig]:
        session = self.create_session()
        try:
            return session.query(AutoScreeningConfig).filter(
                AutoScreeningConfig.user_id == user_id
            ).first()
        finally:
            session.close()

    def get_recent_logs(self, user_id: str, limit: int = 10) -> list:
        from sqlalchemy import desc
        session = self.create_session()
        try:
            return session.query(AutoScreeningLog).filter(
                AutoScreeningLog.user_id == user_id
            ).order_by(desc(AutoScreeningLog.run_date), desc(AutoScreeningLog.id)).limit(limit).all()
        finally:
            session.close()


class AutoScreeningService(BaseService):
    """每日自动筛选配置服务"""

    def __init__(self):
        super().__init__(AutoScreeningRepository())
        self.auto_repo = self.repository

    def get_config(self, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            cfg = self.auto_repo.get_config(user_id)
            if cfg is None:
                return True, '获取成功', {'enabled': False, 'strategy': 'bottom', 'params': None}
            params = {}
            try:
                params = json.loads(cfg.params) if cfg.params else {}
            except (ValueError, TypeError):
                params = {}
            return True, '获取成功', {
                'enabled': bool(cfg.enabled),
                'strategy': cfg.strategy or 'bottom',
                'params': params,
            }
        except Exception as e:
            return False, str(e), None

    def save_config(self, user_id: str, enabled: bool, strategy: str = 'bottom',
                    params: Optional[Dict] = None) -> Tuple[bool, str]:
        try:
            session = self.auto_repo.create_session()
            try:
                cfg = session.query(AutoScreeningConfig).filter(
                    AutoScreeningConfig.user_id == user_id
                ).first()
                if cfg is None:
                    cfg = AutoScreeningConfig(user_id=user_id)
                    session.add(cfg)
                cfg.enabled = 1 if enabled else 0
                cfg.strategy = strategy or 'bottom'
                cfg.params = json.dumps(params or {}, ensure_ascii=False)
                session.commit()
            finally:
                session.close()
            return True, '保存成功'
        except Exception as e:
            return False, str(e)

    def get_recent_logs(self, user_id: str, limit: int = 10) -> Tuple[bool, str, Optional[list]]:
        try:
            logs = self.auto_repo.get_recent_logs(user_id, limit)
            return True, '获取成功', [{
                'run_date': log.run_date.strftime('%Y-%m-%d') if log.run_date else '',
                'added_count': log.added_count,
                'skipped_count': log.skipped_count,
                'error_message': log.error_message or '',
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
            } for log in logs]
        except Exception as e:
            return False, str(e), None
