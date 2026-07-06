#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Tuple
from app.services.base_service import BaseService
from app.repositories.wencai_repository import WencaiRepository
from models import UserStrategy


class WencaiService(BaseService):
    """问财策略服务类"""
    
    def __init__(self):
        super().__init__(WencaiRepository())
        self.wencai_repository = self.repository
    
    def get_strategies(self, user_id: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取用户的问财策略列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            strategies = self.wencai_repository.get_by_user_id(user_id)
            
            result = []
            for strategy in strategies:
                result.append({
                    'id': strategy.id,
                    'strategy_name': strategy.strategy_name,
                    'strategy_type': strategy.strategy_type,
                    'query_template': strategy.query_template,
                    'description': strategy.description,
                    'is_default': strategy.is_default,
                    'created_at': strategy.created_at.isoformat() if strategy.created_at else None,
                    'updated_at': strategy.updated_at.isoformat() if strategy.updated_at else None
                })
            
            return True, '获取成功', result
            
        except Exception as e:
            return False, str(e), None
    
    def create_strategy(self, user_id: str, strategy_name: str, query_template: str,
                       strategy_type: str = 'custom', description: str = '',
                       is_default: int = 0) -> Tuple[bool, str, Optional[Dict]]:
        """
        创建新的问财策略
        
        Args:
            user_id: 用户ID
            strategy_name: 策略名称
            query_template: 查询模板
            strategy_type: 策略类型
            description: 描述
            is_default: 是否默认
            
        Returns:
            tuple: (success, message, data)
        """
        if not strategy_name or not query_template:
            return False, '策略名称和查询模板不能为空', None
        
        try:
            if is_default:
                self.wencai_repository.clear_default_flag(user_id)
            
            strategy = self.wencai_repository.create_strategy(
                user_id, strategy_name, query_template,
                strategy_type, description, is_default
            )
            
            return True, '创建成功', {
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default
            }
            
        except Exception as e:
            return False, str(e), None
    
    def update_strategy(self, strategy_id: int, user_id: str, **kwargs) -> Tuple[bool, str, Optional[Dict]]:
        """
        更新问财策略
        
        Args:
            strategy_id: 策略ID
            user_id: 用户ID
            **kwargs: 更新字段
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            strategy = self.wencai_repository.update_strategy(
                strategy_id, user_id, **kwargs
            )
            
            if not strategy:
                return False, '策略不存在', None
            
            return True, '更新成功', {
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default
            }
            
        except Exception as e:
            return False, str(e), None
    
    def delete_strategy(self, strategy_id: int, user_id: str) -> Tuple[bool, str]:
        """
        删除问财策略
        
        Args:
            strategy_id: 策略ID
            user_id: 用户ID
            
        Returns:
            tuple: (success, message)
        """
        try:
            success = self.wencai_repository.delete_strategy(strategy_id, user_id)
            
            if success:
                return True, '策略已删除'
            else:
                return False, '策略不存在'
                
        except Exception as e:
            return False, str(e)
    
    def query_wencai(self, query: str, cookie: str = '') -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        问财自定义查询
        
        Args:
            query: 查询语句
            cookie: Cookie
            
        Returns:
            tuple: (success, message, data)
        """
        if not query:
            return False, '请提供查询语句', None
        
        try:
            from core.wencai_fetcher import wencai_fetcher
            
            result = wencai_fetcher.custom_query(query, cookie)
            
            if result is None:
                return False, '问财查询失败', None
            
            return True, '查询成功', result
            
        except Exception as e:
            return False, str(e), None
    
    def get_breakout_stocks(self, date_str: str, cookie: str = '') -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取断板日突破120日高点的股票
        
        Args:
            date_str: 日期字符串
            cookie: Cookie
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            from core.wencai_fetcher import wencai_fetcher
            
            stocks = wencai_fetcher.get_breakout_stocks(date_str, cookie)
            
            if stocks is None:
                return False, '问财查询失败', None
            
            return True, '查询成功', stocks
            
        except Exception as e:
            return False, str(e), None
