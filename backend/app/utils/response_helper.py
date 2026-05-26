#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import jsonify
from typing import Any, Dict, List, Optional


class ResponseHelper:
    """响应辅助类"""
    
    @staticmethod
    def success(data: Any = None, message: str = None, **kwargs) -> tuple:
        """
        成功响应
        
        Args:
            data: 返回的数据
            message: 成功消息（可选）
            **kwargs: 额外的字段
            
        Returns:
            tuple: (response, status_code)
        """
        response = {
            'success': True
        }
        if message is not None:
            response['message'] = message
        if data is not None:
            response['data'] = data
        response.update(kwargs)
        return jsonify(response), 200
    
    @staticmethod
    def error(message: str = '操作失败', error_code: int = 400, **kwargs) -> tuple:
        """
        错误响应
        
        Args:
            message: 错误消息
            error_code: 错误代码
            **kwargs: 额外的字段
            
        Returns:
            tuple: (response, status_code)
        """
        response = {
            'success': False,
            'error': message
        }
        response.update(kwargs)
        return jsonify(response), error_code
    
    @staticmethod
    def not_found(message: str = '资源不存在') -> tuple:
        """404响应"""
        return ResponseHelper.error(message, 404)
    
    @staticmethod
    def unauthorized(message: str = '未授权访问') -> tuple:
        """401响应"""
        return ResponseHelper.error(message, 401)
    
    @staticmethod
    def forbidden(message: str = '禁止访问') -> tuple:
        """403响应"""
        return ResponseHelper.error(message, 403)
    
    @staticmethod
    def bad_request(message: str = '请求参数错误') -> tuple:
        """400响应"""
        return ResponseHelper.error(message, 400)
    
    @staticmethod
    def server_error(message: str = '服务器内部错误') -> tuple:
        """500响应"""
        return ResponseHelper.error(message, 500)
    
    @staticmethod
    def paginated(data: List[Any], total: int, page: int, page_size: int, **kwargs) -> tuple:
        """
        分页响应
        
        Args:
            data: 数据列表
            total: 总数
            page: 当前页
            page_size: 每页大小
            **kwargs: 额外的字段
            
        Returns:
            tuple: (response, status_code)
        """
        return ResponseHelper.success(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
            **kwargs
        )
