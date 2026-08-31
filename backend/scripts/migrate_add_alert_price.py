#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 watchlist_stocks 表添加 alert_price（预警价格）字段
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
            print("检查 alert_price 字段是否存在...")
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='watchlist_stocks' AND column_name='alert_price'
            """))

            if result.fetchone():
                print("✓ alert_price 字段已存在，无需迁移")
                return True

            print("添加 alert_price 字段...")
            conn.execute(text("""
                ALTER TABLE watchlist_stocks
                ADD COLUMN alert_price DECIMAL(10, 2)
            """))

            conn.commit()
            print("✓ 成功添加 alert_price 字段")
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n迁移完成！")
    return True


if __name__ == '__main__':
    migrate()
