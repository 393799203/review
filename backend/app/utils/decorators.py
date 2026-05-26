#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from functools import wraps
from flask import request
from app.utils.response_helper import ResponseHelper
from models import User
from datetime import datetime


def get_current_user():
    """获取当前登录用户"""
    uid = request.headers.get('X-User-Uid')
    if not uid:
        return None
    
    from models import DatabaseConfig
    db_config = DatabaseConfig()
    session = db_config.create_session()
    try:
        user = session.query(User).filter(User.uid == uid, User.is_active == 1).first()
        return user
    finally:
        session.close()


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return ResponseHelper.unauthorized('请先登录')
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return ResponseHelper.unauthorized('请先登录')
        if user.role != 'admin':
            return ResponseHelper.forbidden('需要管理员权限')
        return f(*args, **kwargs)
    return decorated_function


def vip_required(f):
    """VIP权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return ResponseHelper.unauthorized('请先登录')
        if not (user.is_vip == 1 and user.vip_expire_date and user.vip_expire_date >= datetime.now().date()):
            return ResponseHelper.forbidden('需要VIP权限')
        return f(*args, **kwargs)
    return decorated_function
