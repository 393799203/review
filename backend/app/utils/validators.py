#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from typing import Optional


def validate_required(value: any, field_name: str) -> Optional[str]:
    """验证必填字段"""
    if not value:
        return f'{field_name}不能为空'
    return None


def validate_email(email: str) -> Optional[str]:
    """验证邮箱格式"""
    if not email:
        return '邮箱不能为空'
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return '邮箱格式不正确'
    return None


def validate_stock_code(code: str) -> Optional[str]:
    """验证股票代码格式"""
    if not code:
        return '股票代码不能为空'
    pattern = r'^[0-9]{6}$'
    if not re.match(pattern, code):
        return '股票代码格式不正确,应为6位数字'
    return None


def validate_password(password: str) -> Optional[str]:
    """验证密码强度"""
    if not password:
        return '密码不能为空'
    if len(password) < 6:
        return '密码长度至少6位'
    if len(password) > 20:
        return '密码长度不能超过20位'
    return None


def validate_username(username: str) -> Optional[str]:
    """验证用户名"""
    if not username:
        return '用户名不能为空'
    if len(username) < 3:
        return '用户名长度至少3位'
    if len(username) > 20:
        return '用户名长度不能超过20位'
    pattern = r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$'
    if not re.match(pattern, username):
        return '用户名只能包含字母、数字、下划线和中文'
    return None
