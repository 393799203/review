#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 blocks 表添加 stock_codes（同花顺板块成分股代码 JSON 数组）
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
            print("检查 stock_codes 字段是否存在...")
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='blocks' AND column_name='stock_codes'
            """))

            if result.fetchone():
                print("✓ stock_codes 字段已存在，无需迁移")
                return True

            print("添加 stock_codes 字段...")
            conn.execute(text("""
                ALTER TABLE blocks
                ADD COLUMN stock_codes TEXT
            """))

            conn.commit()
            print("✓ 成功添加 stock_codes 字段")
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n迁移完成！")
    return True


if __name__ == '__main__':
    migrate()
