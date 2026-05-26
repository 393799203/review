#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.wencai_service import WencaiService


class WencaiController(BaseController):
    """问财策略控制器类"""
    
    def __init__(self):
        super().__init__(WencaiService())
        self.wencai_service = self.service
    
    def get_strategies(self):
        """获取用户的问财策略列表"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未授权', 401)
        
        success, message, data = self.wencai_service.get_strategies(user_id)
        
        if success:
            return self.success(data)
        else:
            return self.error(message, 500)
    
    def create_strategy(self):
        """创建新的问财策略"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未授权', 401)
        
        data = self.get_json_data()
        strategy_name = data.get('strategy_name')
        strategy_type = data.get('strategy_type', 'custom')
        query_template = data.get('query_template')
        description = data.get('description', '')
        is_default = data.get('is_default', 0)
        
        try:
            success, message, data = self.wencai_service.create_strategy(
                user_id, strategy_name, query_template,
                strategy_type, description, is_default
            )
            
            if success:
                return self.success(data, message)
            else:
                if '不能为空' in message:
                    return self.error(message, 400)
                else:
                    return self.error(message, 500)
        except Exception as e:
            error_msg = str(e)
            if 'ForeignKeyViolation' in error_msg or 'foreign key constraint' in error_msg:
                return self.error('用户不存在，无法创建策略', 500)
            else:
                return self.error(error_msg, 500)
    
    def update_strategy(self, strategy_id: int):
        """更新问财策略"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未授权', 401)
        
        data = self.get_json_data()
        
        success, message, result = self.wencai_service.update_strategy(
            strategy_id, user_id, **data
        )
        
        if success:
            return self.success(result, message)
        else:
            if '不存在' in message:
                return self.error(message, 404)
            else:
                return self.error(message, 500)
    
    def delete_strategy(self, strategy_id: int):
        """删除问财策略"""
        user_id = self.get_current_user_uid()
        
        if not user_id:
            return self.error('未授权', 401)
        
        success, message = self.wencai_service.delete_strategy(strategy_id, user_id)
        
        if success:
            return self.success(message=message)
        else:
            return self.error(message, 404)
    
    def query_wencai(self):
        """问财自定义查询"""
        data = self.get_json_data()
        query = data.get('query')
        cookie = data.get('cookie', '')
        
        success, message, result = self.wencai_service.query_wencai(query, cookie)
        
        if success:
            return self.success(result, count=len(result))
        else:
            return self.error(message, 500)
    
    def get_breakout_stocks(self, date_str: str):
        """获取断板日突破120日高点的股票"""
        cookie = self.get_query_param('cookie', '')
        
        success, message, data = self.wencai_service.get_breakout_stocks(date_str, cookie)
        
        if success:
            return self.success(data, count=len(data))
        else:
            return self.error(message, 500)


wencai_controller = WencaiController()
