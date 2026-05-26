#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import uuid as uuid_lib
import secrets
import json
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from app.services.base_service import BaseService
from app.repositories.user_repository import UserRepository
from models import User


class AuthService(BaseService):
    """认证服务类"""
    
    def __init__(self):
        super().__init__(UserRepository())
        self.user_repository = self.repository
    
    def register(self, username: str, email: str, password: str, nickname: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            nickname: 昵称
            
        Returns:
            tuple: (success, message, user_data)
        """
        if not username or not email or not password:
            return False, '用户名、邮箱和密码不能为空', None
        
        existing_user = self.user_repository.get_by_username_or_email(username, email)
        if existing_user:
            return False, '用户名或邮箱已存在', None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = self.user_repository.create(
            uid=str(uuid_lib.uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            nickname=nickname or username
        )
        
        return True, '注册成功', {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'nickname': user.nickname
        }
    
    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            tuple: (success, message, login_data)
        """
        if not username or not password:
            return False, '用户名和密码不能为空', None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = self.user_repository.get_by_username_and_password(username, password_hash)
        if not user:
            return False, '用户名或密码错误', None
        
        self.user_repository.update_last_login(user.uid)
        
        token = secrets.token_hex(32)
        
        return True, '登录成功', {
            'token': token,
            'user': {
                'uid': user.uid,
                'username': user.username,
                'email': user.email,
                'nickname': user.nickname,
                'avatar': user.avatar
            }
        }
    
    def guest_login(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        访客登录
        
        Returns:
            tuple: (success, message, login_data)
        """
        guest_user = self.user_repository.get_by_username('guest')
        
        if not guest_user:
            guest_user = self.user_repository.create(
                uid=str(uuid_lib.uuid4()),
                username='guest',
                email='guest@yunque.ai',
                password_hash='',
                nickname='访客用户',
                role='guest'
            )
        
        self.user_repository.update_last_login(guest_user.uid)
        
        token = secrets.token_hex(32)
        
        return True, '访客登录成功', {
            'token': token,
            'user': {
                'uid': guest_user.uid,
                'username': guest_user.username,
                'email': guest_user.email,
                'nickname': guest_user.nickname,
                'avatar': guest_user.avatar,
                'role': 'guest'
            }
        }
    
    def get_user_info(self, uid: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取用户信息
        
        Args:
            uid: 用户UID
            
        Returns:
            tuple: (success, message, user_info)
        """
        user = self.user_repository.get_by_uid(uid)
        if not user:
            return False, '用户不存在', None
        
        is_vip = False
        vip_status = 'expired'
        
        if user.is_vip == 1 and user.vip_expire_date:
            if user.vip_expire_date >= datetime.now().date():
                is_vip = True
                vip_status = 'active'
            else:
                vip_status = 'expired'
        
        settings = {}
        if user.settings:
            try:
                settings = json.loads(user.settings)
            except:
                settings = {}
        
        return True, '获取成功', {
            'uid': user.uid,
            'username': user.username,
            'email': user.email,
            'nickname': user.nickname,
            'avatar': user.avatar,
            'role': user.role,
            'isVip': is_vip,
            'vipStatus': vip_status,
            'vipExpireDate': user.vip_expire_date.strftime('%Y-%m-%d') if user.vip_expire_date else None,
            'isActive': bool(user.is_active),
            'lastLogin': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            'createdAt': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else None,
            'settings': settings
        }
    
    def get_user_settings(self, uid: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取用户设置
        
        Args:
            uid: 用户UID
            
        Returns:
            tuple: (success, message, settings)
        """
        user = self.user_repository.get_by_uid(uid)
        if not user:
            return False, '用户不存在', None
        
        settings = {}
        if user.settings:
            try:
                settings = json.loads(user.settings)
            except:
                settings = {}
        
        return True, '获取成功', settings
    
    def update_user_settings(self, uid: str, new_settings: Dict) -> Tuple[bool, str]:
        """
        更新用户设置
        
        Args:
            uid: 用户UID
            new_settings: 新设置
            
        Returns:
            tuple: (success, message)
        """
        user = self.user_repository.get_by_uid(uid)
        if not user:
            return False, '用户不存在'
        
        current_settings = {}
        if user.settings:
            try:
                current_settings = json.loads(user.settings)
            except:
                current_settings = {}
        
        current_settings.update(new_settings)
        
        self.user_repository.update_settings(uid, json.dumps(current_settings))
        
        return True, '设置更新成功'
    
    def get_user_stats(self, uid: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取用户统计信息(管理员)
        
        Args:
            uid: 用户UID
            
        Returns:
            tuple: (success, message, stats)
        """
        user = self.user_repository.get_by_uid(uid)
        if not user or user.role != 'admin':
            return False, '权限不足', None
        
        total_users = self.user_repository.count_total_users()
        
        online_threshold = datetime.now() - timedelta(minutes=5)
        online_count = self.user_repository.count_online_users(online_threshold)
        
        user_list = self.user_repository.get_all_users_with_activity(online_threshold)
        
        def sort_key(user):
            is_online = 0 if user['is_online'] else 1
            is_admin = 0 if user['role'] == 'admin' else 1
            is_guest = 1 if user['role'] == 'guest' else 0
            login_count = -(user['login_count'] or 0)
            return (is_guest, is_online, is_admin, login_count)
        
        user_list.sort(key=sort_key)
        
        return True, '获取成功', {
            'total_users': total_users,
            'online_count': online_count,
            'users': user_list
        }
    
    def update_activity(self, uid: str) -> bool:
        """更新用户活动时间"""
        return self.user_repository.update_last_activity(uid)
