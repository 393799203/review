#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List
from datetime import datetime
from sqlalchemy import func
from models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """用户仓库类"""
    
    def __init__(self):
        super().__init__(User)
    
    def get_by_uid(self, uid: str) -> Optional[User]:
        """根据UID获取用户"""
        return self.get_one_by_filter(uid=uid)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.get_one_by_filter(username=username)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.get_one_by_filter(email=email)
    
    def get_by_username_or_email(self, username: str, email: str) -> Optional[User]:
        """根据用户名或邮箱获取用户"""
        session = self.create_session()
        try:
            return session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
        finally:
            session.close()
    
    def get_by_username_and_password(self, username: str, password_hash: str) -> Optional[User]:
        """根据用户名/邮箱和密码哈希获取用户"""
        session = self.create_session()
        try:
            return session.query(User).filter(
                (User.username == username) | (User.email == username),
                User.password_hash == password_hash
            ).first()
        finally:
            session.close()
    
    def get_active_user_by_uid(self, uid: str) -> Optional[User]:
        """获取活跃用户"""
        session = self.create_session()
        try:
            return session.query(User).filter(
                User.uid == uid,
                User.is_active == 1
            ).first()
        finally:
            session.close()
    
    def update_last_login(self, uid: str) -> bool:
        """更新最后登录时间"""
        session = self.create_session()
        try:
            user = session.query(User).filter(User.uid == uid).first()
            if user:
                user.last_login = datetime.now()
                user.login_count = (user.login_count or 0) + 1
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_last_activity(self, uid: str) -> bool:
        """更新最后活动时间"""
        session = self.create_session()
        try:
            user = session.query(User).filter(User.uid == uid).first()
            if user:
                user.last_activity = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_settings(self, uid: str, settings: str) -> bool:
        """更新用户设置"""
        session = self.create_session()
        try:
            user = session.query(User).filter(User.uid == uid).first()
            if user:
                user.settings = settings
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def count_total_users(self) -> int:
        """统计总用户数"""
        session = self.create_session()
        try:
            return session.query(func.count(User.uid)).scalar()
        finally:
            session.close()
    
    def count_online_users(self, threshold: datetime) -> int:
        """统计在线用户数"""
        session = self.create_session()
        try:
            return session.query(func.count(User.uid)).filter(
                User.last_activity >= threshold
            ).scalar()
        finally:
            session.close()
    
    def get_all_users_with_activity(self, threshold: datetime) -> List[dict]:
        """获取所有用户及其活动状态"""
        session = self.create_session()
        try:
            users = session.query(User).all()
            user_list = []
            for u in users:
                is_online = u.last_activity and u.last_activity >= threshold
                user_list.append({
                    'uid': u.uid,
                    'username': u.username,
                    'email': u.email,
                    'nickname': u.nickname,
                    'role': u.role,
                    'login_count': u.login_count or 0,
                    'last_login': u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else None,
                    'last_activity': u.last_activity.strftime('%Y-%m-%d %H:%M:%S') if u.last_activity else None,
                    'is_online': is_online,
                    'created_at': u.created_at.strftime('%Y-%m-%d %H:%M:%S') if u.created_at else None
                })
            return user_list
        finally:
            session.close()

    def count_admins(self) -> int:
        """统计管理员数量"""
        session = self.create_session()
        try:
            return session.query(func.count(User.uid)).filter(
                User.role == 'admin'
            ).scalar() or 0
        finally:
            session.close()

    def delete_with_related(self, uid: str) -> bool:
        """事务删除用户及其关联数据（自选股/交易记录/策略/自动筛选配置/日志）"""
        from models import (WatchlistStock, TradeRecord, UserStrategy,
                            AutoScreeningConfig, AutoScreeningLog)
        session = self.create_session()
        try:
            user = session.query(User).filter(User.uid == uid).first()
            if not user:
                return False
            session.query(WatchlistStock).filter(
                WatchlistStock.user_id == uid
            ).delete(synchronize_session=False)
            session.query(TradeRecord).filter(
                TradeRecord.user_id == uid
            ).delete(synchronize_session=False)
            session.query(UserStrategy).filter(
                UserStrategy.user_id == uid
            ).delete(synchronize_session=False)
            session.query(AutoScreeningConfig).filter(
                AutoScreeningConfig.user_id == uid
            ).delete(synchronize_session=False)
            session.query(AutoScreeningLog).filter(
                AutoScreeningLog.user_id == uid
            ).delete(synchronize_session=False)
            session.delete(user)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
