#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from sqlalchemy import desc
from models import UserWencaiStrategy
from app.repositories.base_repository import BaseRepository


class WencaiRepository(BaseRepository):
    """问财策略仓库类"""
    
    def __init__(self):
        super().__init__(UserWencaiStrategy)
    
    def get_by_user_id(self, user_id: str) -> List[UserWencaiStrategy]:
        """根据用户ID获取策略列表"""
        session = self.create_session()
        try:
            return session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.user_id == user_id
            ).order_by(
                UserWencaiStrategy.is_default.desc(),
                UserWencaiStrategy.created_at.asc()
            ).all()
        finally:
            session.close()
    
    def get_by_id_and_user(self, strategy_id: int, user_id: str) -> Optional[UserWencaiStrategy]:
        """根据ID和用户ID获取策略"""
        session = self.create_session()
        try:
            return session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.id == strategy_id,
                UserWencaiStrategy.user_id == user_id
            ).first()
        finally:
            session.close()
    
    def clear_default_flag(self, user_id: str) -> bool:
        """清除用户的默认策略标记"""
        session = self.create_session()
        try:
            session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.user_id == user_id,
                UserWencaiStrategy.is_default == 1
            ).update({'is_default': 0})
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_strategy(self, user_id: str, strategy_name: str, query_template: str,
                       strategy_type: str = 'custom', description: str = '',
                       is_default: int = 0, enable_skill: int = 1) -> UserWencaiStrategy:
        """创建策略"""
        return self.create(
            user_id=user_id,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            query_template=query_template,
            description=description,
            is_default=is_default,
            enable_skill=enable_skill
        )
    
    def update_strategy(self, strategy_id: int, user_id: str, **kwargs) -> Optional[UserWencaiStrategy]:
        """更新策略"""
        session = self.create_session()
        try:
            strategy = session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.id == strategy_id,
                UserWencaiStrategy.user_id == user_id
            ).first()
            
            if not strategy:
                return None
            
            if 'is_default' in kwargs and kwargs['is_default']:
                self.clear_default_flag(user_id)
            
            for key, value in kwargs.items():
                if hasattr(strategy, key) and value is not None:
                    setattr(strategy, key, value)
            
            session.commit()
            session.refresh(strategy)
            return strategy
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_strategy(self, strategy_id: int, user_id: str) -> bool:
        """删除策略"""
        session = self.create_session()
        try:
            strategy = session.query(UserWencaiStrategy).filter(
                UserWencaiStrategy.id == strategy_id,
                UserWencaiStrategy.user_id == user_id
            ).first()
            
            if not strategy:
                return False
            
            session.delete(strategy)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
