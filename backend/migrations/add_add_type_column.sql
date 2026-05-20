-- 添加 add_type 字段到 watchlist_stocks 表
-- 执行时间: 2026-05-20

-- 添加 add_type 字段
ALTER TABLE watchlist_stocks 
ADD COLUMN IF NOT EXISTS add_type VARCHAR(20) DEFAULT 'manual';

-- 更新现有数据，根据 source 字段判断类型
UPDATE watchlist_stocks 
SET add_type = CASE 
    WHEN source = 'wencai' THEN 'strategy'
    ELSE 'manual'
END
WHERE add_type IS NULL OR add_type = 'manual';

-- 添加注释
COMMENT ON COLUMN watchlist_stocks.add_type IS '加入类型: manual-手动加入, strategy-策略加入';
