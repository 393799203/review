#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import request
from app.controllers.base_controller import BaseController
from app.services.auth_service import AuthService
from app.utils.decorators import admin_required


class AuthController(BaseController):
    """认证控制器类"""
    
    def __init__(self):
        super().__init__(AuthService())
        self.auth_service = self.service
    
    def register(self):
        """用户注册"""
        data = self.get_json_data()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        nickname = data.get('nickname', username)
        
        success, message, user_data = self.auth_service.register(
            username, email, password, nickname
        )
        
        if success:
            return self.success(user_data, message)
        else:
            return self.error(message, 400)
    
    def login(self):
        """用户登录"""
        data = self.get_json_data()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return self.error('用户名和密码不能为空', 400)
        
        success, message, login_data = self.auth_service.login(username, password)
        
        if success:
            return self.success(login_data, message)
        else:
            return self.error(message, 401)
    
    def guest_login(self):
        """访客登录"""
        success, message, login_data = self.auth_service.guest_login()
        
        if success:
            return self.success(login_data, message)
        else:
            return self.error(message, 500)
    
    def get_current_user(self):
        """获取当前用户信息"""
        uid = self.get_current_user_uid()
        
        if not uid:
            return self.error('未登录', 401, code='UNAUTHORIZED')
        
        success, message, user_info = self.auth_service.get_user_info(uid)
        
        if success:
            return self.success(user_info, message)
        else:
            return self.error(message, 404, code='USER_NOT_FOUND')
    
    def logout(self):
        """用户登出"""
        return self.success(message='登出成功')
    
    def get_settings(self):
        """获取用户设置"""
        uid = self.get_current_user_uid()
        
        if not uid:
            return self.error('未登录', 401)
        
        success, message, settings = self.auth_service.get_user_settings(uid)
        
        if success:
            return self.success({'settings': settings}, message)
        else:
            return self.error(message, 404)
    
    def update_settings(self):
        """更新用户设置"""
        uid = self.get_current_user_uid()
        
        if not uid:
            return self.error('未登录', 401, code='UNAUTHORIZED')
        
        data = self.get_json_data()
        new_settings = data.get('settings', data)
        
        success, message = self.auth_service.update_user_settings(uid, new_settings)
        
        if success:
            return self.success(message=message)
        else:
            return self.error(message, 404, code='USER_NOT_FOUND')
    
    def get_user_stats(self):
        """获取用户统计信息(管理员)"""
        uid = self.get_current_user_uid()
        
        if not uid:
            return self.error('权限不足', 403)
        
        success, message, stats = self.auth_service.get_user_stats(uid)
        
        if success:
            return self.success(stats, message)
        else:
            return self.error(message, 403)
    
    def update_activity(self, uid: str):
        """更新用户活动时间"""
        return self.auth_service.update_activity(uid)


auth_controller = AuthController()
