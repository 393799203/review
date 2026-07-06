#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：将 user_wencai_strategies 表改为 user_strategies
并添加 strategy_type 字段的索引
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from sqlalchemy import text

def migrate_strategy_table():
    """迁移策略表"""
    session = get_db_session()
    
    try:
        print("开始迁移策略表...")
        
        # 1. 检查旧表是否存在
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_wencai_strategies'
            );
        """))
        
        old_table_exists = result.scalar()
        
        if old_table_exists:
            print("✓ 发现旧表 user_wencai_strategies")
            
            # 2. 创建新表
            print("创建新表 user_strategies...")
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_strategies (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
                    strategy_name VARCHAR(100) NOT NULL,
                    strategy_type VARCHAR(50) DEFAULT 'wencai',
                    query_template TEXT NOT NULL,
                    description VARCHAR(500),
                    is_default INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            session.commit()
            print("✓ 新表创建成功")
            
            # 3. 迁移数据
            print("迁移数据...")
            session.execute(text("""
                INSERT INTO user_strategies 
                (id, user_id, strategy_name, strategy_type, query_template, description, is_default, created_at, updated_at)
                SELECT 
                id, user_id, strategy_name, 
                CASE 
                    WHEN strategy_type = 'comparable' THEN 'comparable'
                    ELSE 'wencai'
                END as strategy_type,
                query_template, description, is_default, created_at, updated_at
                FROM user_wencai_strategies;
            """))
            session.commit()
            
            # 查看迁移的数据数量
            result = session.execute(text("SELECT COUNT(*) FROM user_strategies;"))
            count = result.scalar()
            print(f"✓ 已迁移 {count} 条策略数据")
            
            # 4. 创建索引
            print("创建索引...")
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_strategy_user_id ON user_strategies(user_id);
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_strategy_type ON user_strategies(strategy_type);
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_strategy_is_default ON user_strategies(is_default);
            """))
            session.commit()
            print("✓ 索引创建成功")
            
            # 5. 删除旧表
            print("删除旧表...")
            session.execute(text("DROP TABLE user_wencai_strategies;"))
            session.commit()
            print("✓ 旧表已删除")
            
        else:
            print("✓ 旧表不存在，检查新表...")
            
            # 检查新表是否存在
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'user_strategies'
                );
            """))
            
            new_table_exists = result.scalar()
            
            if not new_table_exists:
                print("创建新表 user_strategies...")
                session.execute(text("""
                    CREATE TABLE user_strategies (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
                        strategy_name VARCHAR(100) NOT NULL,
                        strategy_type VARCHAR(50) DEFAULT 'wencai',
                        query_template TEXT NOT NULL,
                        description VARCHAR(500),
                        is_default INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                session.commit()
                print("✓ 新表创建成功")
                
                # 创建索引
                print("创建索引...")
                session.execute(text("""
                    CREATE INDEX idx_strategy_user_id ON user_strategies(user_id);
                """))
                session.execute(text("""
                    CREATE INDEX idx_strategy_type ON user_strategies(strategy_type);
                """))
                session.execute(text("""
                    CREATE INDEX idx_strategy_is_default ON user_strategies(is_default);
                """))
                session.commit()
                print("✓ 索引创建成功")
            else:
                print("✓ 新表已存在")
        
        print("\n迁移完成！")
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    migrate_strategy_table()