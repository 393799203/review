#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""
from database import get_db_session, init_db
from models import Base
import sys

def main():
    """初始化数据库表结构"""
    try:
        print("开始初始化数据库表结构...")
        init_db()
        print("数据库表结构初始化完成!")

        # 检查表是否创建成功
        session = get_db_session()
        from sqlalchemy import inspect
        inspector = inspect(session.bind)
        tables = inspector.get_table_names()
        print(f"成功创建的表: {tables}")
        session.close()

        return True
    except Exception as e:
        print(f"初始化失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)