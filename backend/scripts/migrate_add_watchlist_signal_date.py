#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移：为 watchlist_stocks 添加 signal_date（放量首日）字段
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models import DatabaseConfig


def migrate():
    db_config = DatabaseConfig()
    engine = create_engine(db_config.get_database_url(), echo=True)

    try:
        with engine.connect() as conn:
            print("检查 signal_date 字段是否存在...")
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='watchlist_stocks' AND column_name='signal_date'
            """))
            if result.fetchone():
                print("✓ signal_date 字段已存在，无需迁移")
                return True
            print("添加 signal_date 字段...")
            conn.execute(text("ALTER TABLE watchlist_stocks ADD COLUMN signal_date DATE"))
            conn.commit()
            print("✓ 成功添加 signal_date 字段")
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("迁移完成！")
    return True


if __name__ == '__main__':
    migrate()
