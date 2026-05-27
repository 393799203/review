#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建hot_topic_analysis_results表
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
            print("检查hot_topic_analysis_results表是否存在...")
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='hot_topic_analysis_results'
            """))
            
            if result.fetchone():
                print("✓ hot_topic_analysis_results表已存在，无需迁移")
                return
            
            print("创建hot_topic_analysis_results表...")
            conn.execute(text("""
                CREATE TABLE hot_topic_analysis_results (
                    id SERIAL PRIMARY KEY,
                    topic_title VARCHAR(500) NOT NULL,
                    analysis_result TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_hot_topic_title UNIQUE (topic_title)
                )
            """))
            
            conn.commit()
            print("✓ 成功创建hot_topic_analysis_results表")
            
            print("创建索引...")
            conn.execute(text("""
                CREATE INDEX idx_hot_topic_title ON hot_topic_analysis_results(topic_title)
            """))
            
            conn.commit()
            print("✓ 成功创建索引")
            
    except Exception as e:
        print(f"✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n迁移完成！")
    return True


if __name__ == '__main__':
    migrate()
