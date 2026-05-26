#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from flask_mail import Message
from app.controllers.base_controller import BaseController
from app.repositories.user_repository import UserRepository
from database import mail


class AdminController(BaseController):
    """管理员接口控制器类"""
    
    def __init__(self):
        super().__init__(None)
        self.user_repository = UserRepository()
    
    def send_welcome_email(self):
        """发送欢迎邮件"""
        try:
            uid = self.get_current_user_uid()
            
            user = self.user_repository.get_by_uid(uid)
            
            if not user or user.role != 'admin':
                return self.error('权限不足', 403)
            
            data = self.get_json_data()
            target_email = data.get('email')
            username = data.get('username', '用户')
            
            if not target_email:
                return self.error('邮箱地址不能为空', 400)
            
            from core.email_utils import send_welcome_email_to_user
            
            if send_welcome_email_to_user(target_email, username):
                return self.success(message=f'已成功向 {target_email} 发送欢迎邮件')
            else:
                return self.error('发送邮件失败,请检查邮件服务配置', 500)
                
        except Exception as e:
            return self.error(f'发送邮件失败:{str(e)}', 500)
    
    def send_custom_email(self):
        """发送自定义邮件"""
        try:
            uid = self.get_current_user_uid()
            
            user = self.user_repository.get_by_uid(uid)
            
            if not user or user.role != 'admin':
                return self.error('权限不足', 403)
            
            data = self.get_json_data()
            target_email = data.get('email')
            subject = data.get('subject')
            content = data.get('content')
            
            if not target_email:
                return self.error('邮箱地址不能为空', 400)
            
            if not subject:
                return self.error('邮件主题不能为空', 400)
            
            if not content:
                return self.error('邮件内容不能为空', 400)
            
            mail_password = os.environ.get('MAIL_PASSWORD')
            if not mail_password:
                return self.error('邮件服务未配置:缺少 MAIL_PASSWORD 环境变量', 500)
            
            msg = Message(
                subject=subject,
                recipients=[target_email],
                html=content
            )
            
            with mail.connect() as conn:
                conn.send(msg)
            
            return self.success(message=f'已成功向 {target_email} 发送邮件')
                
        except Exception as e:
            return self.error(f'发送邮件失败:{str(e)}', 500)


admin_controller = AdminController()
