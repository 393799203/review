#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：创建keyword_analysis表
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
            print("检查keyword_analysis表是否存在...")
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='keyword_analysis'
            """))
            
            if result.fetchone():
                print("✓ keyword_analysis表已存在，无需迁移")
                return
            
            print("创建keyword_analysis表...")
            conn.execute(text("""
                CREATE TABLE keyword_analysis (
                    id SERIAL PRIMARY KEY,
                    trade_date DATE NOT NULL,
                    raw_keywords TEXT,
                    merged_keywords TEXT,
                    analysis_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_keyword_analysis_trade_date UNIQUE (trade_date)
                )
            """))
            
            conn.commit()
            print("✓ 成功创建keyword_analysis表")
            
            print("创建索引...")
            conn.execute(text("""
                CREATE UNIQUE INDEX idx_ka_trade_date ON keyword_analysis(trade_date)
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
