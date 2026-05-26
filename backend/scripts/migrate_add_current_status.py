#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加current_status字段到limit_up_stocks表
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models import DatabaseConfig


def migrate():
    """执行数据库迁移"""
    db_config = DatabaseConfig()
    engine = create_engine(db_config.get_database_url(), echo=True)
    
    try:
        with engine.connect() as conn:
            print("检查current_status字段是否存在...")
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='limit_up_stocks' AND column_name='current_status'
            """))
            
            if result.fetchone():
                print("✓ current_status字段已存在，无需迁移")
                return
            
            print("添加current_status字段...")
            conn.execute(text("""
                ALTER TABLE limit_up_stocks 
                ADD COLUMN current_status VARCHAR(20) DEFAULT 'close'
            """))
            
            conn.commit()
            print("✓ 成功添加current_status字段")
            
            print("更新现有数据...")
            conn.execute(text("""
                UPDATE limit_up_stocks 
                SET current_status = 'close'
                WHERE current_status IS NULL
            """))
            
            conn.commit()
            print("✓ 已更新现有数据的current_status字段")
            
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n迁移完成！")
    return True


if __name__ == '__main__':
    migrate()