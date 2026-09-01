#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移：创建每日自动筛选相关表
- auto_screening_config（用户开关 + 参数）
- auto_screening_logs（执行日志）
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
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS auto_screening_config (
                    user_id VARCHAR(36) PRIMARY KEY REFERENCES users(uid),
                    enabled INTEGER NOT NULL DEFAULT 0,
                    strategy VARCHAR(20) NOT NULL DEFAULT 'bottom',
                    params TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS auto_screening_logs (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
                    run_date DATE NOT NULL,
                    added_count INTEGER NOT NULL DEFAULT 0,
                    skipped_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_auto_screening_user_date
                ON auto_screening_logs (user_id, run_date)
            """))
            conn.commit()
            print("✓ 已创建 auto_screening_config / auto_screening_logs 表")
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("迁移完成！")
    return True


if __name__ == '__main__':
    migrate()
