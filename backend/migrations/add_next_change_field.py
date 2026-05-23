#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加 next_change 字段
用于记录昨日涨停股票的次日涨跌幅

执行方式：
python migrations/add_next_change_field.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models import DatabaseConfig

def migrate():
    """执行数据库迁移"""
    db_config = DatabaseConfig()
    session = db_config.create_session()
    
    try:
        print("开始执行数据库迁移...")
        
        # 检查字段是否已存在
        check_sql = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='limit_up_stocks' 
            AND column_name='next_change'
        """)
        result = session.execute(check_sql).fetchone()
        
        if result:
            print("✓ next_change 字段已存在，跳过迁移")
            return
        
        # 添加字段
        alter_sql = text("ALTER TABLE limit_up_stocks ADD COLUMN next_change NUMERIC(10, 4)")
        session.execute(alter_sql)
        session.commit()
        print("✓ 成功添加 next_change 字段")
        
        # 添加注释
        comment_sql = text("COMMENT ON COLUMN limit_up_stocks.next_change IS '次日涨跌幅(%)'")
        session.execute(comment_sql)
        session.commit()
        print("✓ 成功添加字段注释")
        
        print("\n迁移完成！")
        
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    migrate()
