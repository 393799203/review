#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日自动筛选配置控制器"""

from app.controllers.base_controller import BaseController
from app.services.auto_screening_service import AutoScreeningService


class AutoScreeningController(BaseController):
    """每日自动筛选配置控制器"""

    def __init__(self):
        super().__init__(AutoScreeningService())
        self.auto_service = self.service

    def get_config(self):
        """获取当前用户某策略的自动筛选配置"""
        user_id = self.get_current_user_uid()
        if not user_id:
            return self.error('未提供用户ID', 401)
        strategy = str(self.get_query_param('strategy', 'bottom'))
        success, message, data = self.auto_service.get_config(user_id, strategy)
        if success:
            return self.success(data)
        return self.error(message, 500)

    def save_config(self):
        """保存当前用户自动筛选配置"""
        user_id = self.get_current_user_uid()
        if not user_id:
            return self.error('未提供用户ID', 401)
        data = self.get_json_data()
        enabled = bool(data.get('enabled', False))
        strategy = str(data.get('strategy', 'bottom'))
        params = data.get('params') or {}
        success, message = self.auto_service.save_config(user_id, enabled, strategy, params)
        if success:
            return self.success(message=message)
        return self.error(message, 400)

    def get_logs(self):
        """获取当前用户自动筛选执行日志"""
        user_id = self.get_current_user_uid()
        if not user_id:
            return self.error('未提供用户ID', 401)
        limit = int(self.get_query_param('limit', 10))
        success, message, data = self.auto_service.get_recent_logs(user_id, limit)
        if success:
            return self.success(data)
        return self.error(message, 500)

    def run_now(self):
        """手动立即执行一次自动筛选（当前用户 + 指定策略）"""
        user_id = self.get_current_user_uid()
        if not user_id:
            return self.error('未提供用户ID', 401)
        data = self.get_json_data()
        strategy = str(data.get('strategy', 'bottom'))
        try:
            from database import get_db_session
            from models import AutoScreeningConfig
            session = get_db_session()
            try:
                cfg = session.query(AutoScreeningConfig).filter(
                    AutoScreeningConfig.user_id == user_id,
                    AutoScreeningConfig.strategy == strategy,
                ).first()
                if cfg is None:
                    cfg = AutoScreeningConfig(
                        user_id=user_id, strategy=strategy,
                        enabled=1, params=None,
                    )
                    session.add(cfg)
                    session.commit()
                from app.core.auto_screening_job import _run_for_user
                _run_for_user(cfg, session)
            finally:
                session.close()
            return self.success(message='执行完成，请到自选股查看')
        except Exception as e:
            return self.error(f'执行失败: {e}', 500)


auto_screening_controller = AutoScreeningController()
