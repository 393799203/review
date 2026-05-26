#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import request
from typing import Any, Dict, Optional
from app.services.base_service import BaseService
from app.utils.response_helper import ResponseHelper


class BaseController:
    """基础控制器类"""
    
    def __init__(self, service: BaseService):
        """
        初始化控制器
        
        Args:
            service: 服务实例
        """
        self.service = service
    
    def get_json_data(self) -> Dict:
        """获取JSON请求数据"""
        return request.get_json() or {}
    
    def get_query_param(self, key: str, default: Any = None) -> Any:
        """获取查询参数"""
        return request.args.get(key, default)
    
    def get_current_user_uid(self) -> Optional[str]:
        """获取当前用户UID"""
        return request.headers.get('X-User-Uid')
    
    def success(self, data: Any = None, message: str = None, **kwargs) -> tuple:
        """成功响应"""
        return ResponseHelper.success(data, message, **kwargs)
    
    def error(self, message: str = '操作失败', error_code: int = 400, **kwargs) -> tuple:
        """错误响应"""
        return ResponseHelper.error(message, error_code, **kwargs)
    
    def not_found(self, message: str = '资源不存在') -> tuple:
        """404响应"""
        return ResponseHelper.not_found(message)
    
    def unauthorized(self, message: str = '未授权访问') -> tuple:
        """401响应"""
        return ResponseHelper.unauthorized(message)
    
    def forbidden(self, message: str = '禁止访问') -> tuple:
        """403响应"""
        return ResponseHelper.forbidden(message)
    
    def bad_request(self, message: str = '请求参数错误') -> tuple:
        """400响应"""
        return ResponseHelper.bad_request(message)
    
    def server_error(self, message: str = '服务器内部错误') -> tuple:
        """500响应"""
        return ResponseHelper.server_error(message)
    
    def paginated(self, data: list, total: int, page: int, page_size: int, **kwargs) -> tuple:
        """分页响应"""
        return ResponseHelper.paginated(data, total, page, page_size, **kwargs)
    
    def get_page_params(self) -> tuple:
        """获取分页参数"""
        page = int(self.get_query_param('page', 1))
        page_size = int(self.get_query_param('page_size', 20))
        return page, page_size
