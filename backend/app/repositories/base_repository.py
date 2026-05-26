#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import List, Optional, Type, TypeVar, Any
from sqlalchemy.orm import Query
from models import DatabaseConfig

T = TypeVar('T')


class BaseRepository:
    """基础仓库类"""
    
    def __init__(self, model_class: Type[T]):
        """
        初始化仓库
        
        Args:
            model_class: 模型类
        """
        self.model_class = model_class
        self.db_config = DatabaseConfig()
    
    def create_session(self):
        """创建数据库会话"""
        return self.db_config.create_session()
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取记录"""
        session = self.create_session()
        try:
            return session.query(self.model_class).filter(self.model_class.id == id).first()
        finally:
            session.close()
    
    def get_all(self) -> List[T]:
        """获取所有记录"""
        session = self.create_session()
        try:
            return session.query(self.model_class).all()
        finally:
            session.close()
    
    def get_by_filter(self, **filters) -> List[T]:
        """根据条件获取记录"""
        session = self.create_session()
        try:
            query = session.query(self.model_class)
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            return query.all()
        finally:
            session.close()
    
    def get_one_by_filter(self, **filters) -> Optional[T]:
        """根据条件获取单条记录"""
        session = self.create_session()
        try:
            query = session.query(self.model_class)
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            return query.first()
        finally:
            session.close()
    
    def create(self, **kwargs) -> T:
        """创建记录"""
        session = self.create_session()
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update(self, instance: T, **kwargs) -> T:
        """更新记录"""
        session = self.create_session()
        try:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            session.merge(instance)
            session.commit()
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete(self, instance: T) -> bool:
        """删除记录"""
        session = self.create_session()
        try:
            session.delete(instance)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_by_id(self, id: int) -> bool:
        """根据ID删除记录"""
        session = self.create_session()
        try:
            instance = session.query(self.model_class).filter(self.model_class.id == id).first()
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def count(self, **filters) -> int:
        """统计记录数"""
        session = self.create_session()
        try:
            query = session.query(self.model_class)
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    query = query.filter(getattr(self.model_class, key) == value)
            return query.count()
        finally:
            session.close()
    
    def exists(self, **filters) -> bool:
        """判断记录是否存在"""
        return self.count(**filters) > 0
    
    def paginate(self, query: Query, page: int = 1, page_size: int = 20) -> dict:
        """
        分页查询
        
        Args:
            query: 查询对象
            page: 页码
            page_size: 每页大小
            
        Returns:
            dict: 包含items, total, page, page_size的字典
        """
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size
        }
