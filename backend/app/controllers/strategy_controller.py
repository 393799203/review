#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一策略控制器
提供统一的策略管理接口，支持通过 strategy_type 区分不同类型的策略
"""

from flask import request, jsonify
from app.controllers.base_controller import BaseController
from app.services.wencai_service import WencaiService
from database import get_db_session
from models import UserStrategy
import logging

logger = logging.getLogger(__name__)


class StrategyController(BaseController):
    """统一策略控制器类"""
    
    def __init__(self):
        super().__init__(WencaiService())
        self.strategy_service = self.service
    
    def get_strategies(self):
        """
        获取用户的策略列表
        
        Query params:
        - strategy_type: 策略类型（wencai 或 comparable）
        """
        try:
            user_id = self.get_current_user_uid()
            
            if not user_id:
                return self.error('未授权', 401)
            
            # 从查询参数获取策略类型
            strategy_type = request.args.get('strategy_type', None)
            
            session = get_db_session()
            
            # 构建查询条件
            query = session.query(UserStrategy).filter_by(user_id=user_id)
            
            # 如果指定了策略类型，添加过滤条件
            if strategy_type:
                query = query.filter_by(strategy_type=strategy_type)
            
            strategies = query.order_by(
                UserStrategy.is_default.desc(),
                UserStrategy.created_at.desc()
            ).all()
            
            result = []
            for s in strategies:
                result.append({
                    'id': s.id,
                    'strategy_name': s.strategy_name,
                    'strategy_type': s.strategy_type,
                    'query_template': s.query_template,
                    'description': s.description,
                    'is_default': s.is_default,
                    'created_at': s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else None,
                    'updated_at': s.updated_at.strftime('%Y-%m-%d %H:%M:%S') if s.updated_at else None
                })
            
            session.close()
            return self.success(result)
            
        except Exception as e:
            logger.error(f"获取策略列表失败: {str(e)}")
            return self.error(str(e), 500)
    
    def create_strategy(self):
        """
        创建新策略
        
        Request JSON:
        {
            "strategy_name": "策略名称",
            "strategy_type": "wencai 或 comparable",
            "query_template": "策略内容",
            "description": "策略描述",
            "is_default": false
        }
        """
        try:
            user_id = self.get_current_user_uid()
            
            if not user_id:
                return self.error('未授权', 401)
            
            data = request.json
            strategy_name = data.get('strategy_name')
            strategy_type = data.get('strategy_type', 'wencai')
            query_template = data.get('query_template')
            description = data.get('description', '')
            is_default = data.get('is_default', False)
            
            if not strategy_name or not query_template:
                return self.error('策略名称和内容不能为空', 400)
            
            # 验证策略类型
            valid_types = ['wencai', 'comparable']
            if strategy_type not in valid_types:
                return self.error(f'策略类型必须是 {valid_types} 之一', 400)
            
            session = get_db_session()
            
            # 如果设置为默认策略，先清除该类型的其他默认策略
            if is_default:
                session.query(UserStrategy).filter(
                    UserStrategy.user_id == user_id,
                    UserStrategy.strategy_type == strategy_type,
                    UserStrategy.is_default == 1
                ).update({'is_default': 0})
            
            new_strategy = UserStrategy(
                user_id=user_id,
                strategy_name=strategy_name,
                strategy_type=strategy_type,
                query_template=query_template,
                description=description,
                is_default=1 if is_default else 0
            )
            
            session.add(new_strategy)
            session.commit()
            
            result = {
                'id': new_strategy.id,
                'strategy_name': new_strategy.strategy_name,
                'strategy_type': new_strategy.strategy_type,
                'query_template': new_strategy.query_template,
                'description': new_strategy.description,
                'is_default': new_strategy.is_default,
                'created_at': new_strategy.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            session.close()
            return self.success(result, '策略创建成功')
            
        except Exception as e:
            logger.error(f"创建策略失败: {str(e)}")
            return self.error(str(e), 500)
    
    def update_strategy(self, strategy_id):
        """
        更新策略
        
        Request JSON:
        {
            "strategy_name": "策略名称",
            "query_template": "策略内容",
            "description": "策略描述",
            "is_default": false
        }
        """
        try:
            user_id = self.get_current_user_uid()
            
            if not user_id:
                return self.error('未授权', 401)
            
            data = request.json
            strategy_name = data.get('strategy_name')
            query_template = data.get('query_template')
            description = data.get('description')
            is_default = data.get('is_default')
            
            session = get_db_session()
            strategy = session.query(UserStrategy).filter_by(
                id=strategy_id,
                user_id=user_id
            ).first()
            
            if not strategy:
                session.close()
                return self.error('策略不存在', 404)
            
            # 如果设置为默认策略，先清除该类型的其他默认策略
            if is_default:
                session.query(UserStrategy).filter(
                    UserStrategy.user_id == user_id,
                    UserStrategy.strategy_type == strategy.strategy_type,
                    UserStrategy.is_default == 1,
                    UserStrategy.id != strategy_id
                ).update({'is_default': 0})
            
            # 更新策略字段
            if strategy_name:
                strategy.strategy_name = strategy_name
            if query_template:
                strategy.query_template = query_template
            if description:
                strategy.description = description
            if is_default is not None:
                strategy.is_default = 1 if is_default else 0
            
            session.commit()
            
            result = {
                'id': strategy.id,
                'strategy_name': strategy.strategy_name,
                'strategy_type': strategy.strategy_type,
                'query_template': strategy.query_template,
                'description': strategy.description,
                'is_default': strategy.is_default,
                'created_at': strategy.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': strategy.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            session.close()
            return self.success(result, '策略更新成功')
            
        except Exception as e:
            logger.error(f"更新策略失败: {str(e)}")
            return self.error(str(e), 500)
    
    def delete_strategy(self, strategy_id):
        """
        删除策略
        
        Args:
            strategy_id: 策略ID
        """
        try:
            user_id = self.get_current_user_uid()
            
            if not user_id:
                return self.error('未授权', 401)
            
            session = get_db_session()
            strategy = session.query(UserStrategy).filter_by(
                id=strategy_id,
                user_id=user_id
            ).first()
            
            if not strategy:
                session.close()
                return self.error('策略不存在', 404)
            
            session.delete(strategy)
            session.commit()
            session.close()
            
            return self.success(message='策略删除成功')
            
        except Exception as e:
            logger.error(f"删除策略失败: {str(e)}")
            return self.error(str(e), 500)


strategy_controller = StrategyController()