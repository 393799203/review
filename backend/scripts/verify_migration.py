#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据库迁移结果
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models import DatabaseConfig


def verify_migration():
    """验证迁移结果"""
    db_config = DatabaseConfig()
    engine = create_engine(db_config.get_database_url(), echo=False)
    
    try:
        with engine.connect() as conn:
            print("验证数据库迁移结果...")
            
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name='limit_up_stocks' AND column_name='current_status'
            """))
            
            row = result.fetchone()
            if row:
                print(f"✓ current_status字段存在")
                print(f"  数据类型: {row[1]}")
                print(f"  默认值: {row[2]}")
            else:
                print("✗ current_status字段不存在")
                return False
            
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN current_status = 'close' THEN 1 END) as close_count,
                       COUNT(CASE WHEN current_status = 'open' THEN 1 END) as open_count
                FROM limit_up_stocks
            """))
            
            row = result.fetchone()
            print(f"\n✓ 数据统计:")
            print(f"  总记录数: {row[0]}")
            print(f"  封板状态: {row[1]}")
            print(f"  开板状态: {row[2]}")
            
            result = conn.execute(text("""
                SELECT stock_code, stock_name, current_status, trade_date
                FROM limit_up_stocks
                ORDER BY trade_date DESC
                LIMIT 5
            """))
            
            print(f"\n✓ 最新5条记录示例:")
            for row in result:
                print(f"  {row[0]} {row[1]} - {row[2]} ({row[3]})")
            
    except Exception as e:
        print(f"✗ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n验证完成！")
    return True


if __name__ == '__main__':
    verify_migration()