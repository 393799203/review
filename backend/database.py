#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask_mail import Mail
from models import DatabaseConfig

db_config = DatabaseConfig()

mail = None


def init_mail(flask_app):
    """初始化邮件服务"""
    global mail
    mail = Mail(flask_app)


def get_db_session():
    """获取数据库会话"""
    return db_config.create_session()
