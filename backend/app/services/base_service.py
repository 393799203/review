#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from app.repositories.base_repository import BaseRepository


class BaseService:
    """基础服务类"""
    
    def __init__(self, repository: BaseRepository):
        """
        初始化服务
        
        Args:
            repository: 仓库实例
        """
        self.repository = repository
    
    def get_by_id(self, id: int) -> Optional[Any]:
        """根据ID获取记录"""
        return self.repository.get_by_id(id)
    
    def get_all(self) -> List[Any]:
        """获取所有记录"""
        return self.repository.get_all()
    
    def get_by_filter(self, **filters) -> List[Any]:
        """根据条件获取记录"""
        return self.repository.get_by_filter(**filters)
    
    def get_one_by_filter(self, **filters) -> Optional[Any]:
        """根据条件获取单条记录"""
        return self.repository.get_one_by_filter(**filters)
    
    def create(self, **kwargs) -> Any:
        """创建记录"""
        return self.repository.create(**kwargs)
    
    def update(self, instance: Any, **kwargs) -> Any:
        """更新记录"""
        return self.repository.update(instance, **kwargs)
    
    def delete(self, instance: Any) -> bool:
        """删除记录"""
        return self.repository.delete(instance)
    
    def delete_by_id(self, id: int) -> bool:
        """根据ID删除记录"""
        return self.repository.delete_by_id(id)
    
    def count(self, **filters) -> int:
        """统计记录数"""
        return self.repository.count(**filters)
    
    def exists(self, **filters) -> bool:
        """判断记录是否存在"""
        return self.repository.exists(**filters)
    
    def to_dict(self, instance: Any, exclude: List[str] = None) -> Dict:
        """
        将模型实例转换为字典
        
        Args:
            instance: 模型实例
            exclude: 排除的字段列表
            
        Returns:
            dict: 字典表示
        """
        if not instance:
            return {}
        
        exclude = exclude or []
        result = {}
        for column in instance.__table__.columns:
            if column.name not in exclude:
                value = getattr(instance, column.name)
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                result[column.name] = value
        return result
    
    def to_list(self, instances: List[Any], exclude: List[str] = None) -> List[Dict]:
        """
        将模型实例列表转换为字典列表
        
        Args:
            instances: 模型实例列表
            exclude: 排除的字段列表
            
        Returns:
            list: 字典列表
        """
        return [self.to_dict(instance, exclude) for instance in instances]
