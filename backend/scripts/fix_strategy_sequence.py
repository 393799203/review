#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库主键序列问题
解决主键冲突：duplicate key value violates unique constraint
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_session
from sqlalchemy import text

def fix_sequence():
    """修复 user_strategies 表的序列"""
    session = get_db_session()
    
    try:
        print("开始修复主键序列...")
        
        # 1. 查询当前最大的ID
        result = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM user_strategies;"))
        max_id = result.scalar()
        print(f"当前最大ID: {max_id}")
        
        # 2. 设置序列的下一个值为 max_id + 1
        session.execute(text(f"SELECT setval('user_strategies_id_seq', {max_id + 1}, false);"))
        session.commit()
        print(f"✓ 序列已设置为 {max_id + 1}")
        
        # 3. 验证序列值
        result = session.execute(text("SELECT last_value FROM user_strategies_id_seq;"))
        last_value = result.scalar()
        print(f"✓ 当前序列值: {last_value}")
        
        print("\n修复完成！")
        
    except Exception as e:
        print(f"\n✗ 修复失败: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == '__main__':
    fix_sequence()