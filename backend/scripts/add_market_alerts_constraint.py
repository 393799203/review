#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为 market_alerts 表添加唯一约束
解决 ON CONFLICT 错误
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from sqlalchemy import text

def add_unique_constraint():
    """为 market_alerts 表添加唯一约束"""
    session = get_db_session()
    
    try:
        print("开始添加唯一约束...")
        
        # 添加 (stock_code, alert_type) 的唯一约束
        print("添加 (stock_code, alert_type) 唯一约束...")
        session.execute(text("""
            ALTER TABLE market_alerts 
            ADD CONSTRAINT unique_stock_alert 
            UNIQUE (stock_code, alert_type);
        """))
        session.commit()
        print("✓ 唯一约束添加成功")
        
        print("\n迁移完成！")
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    add_unique_constraint()