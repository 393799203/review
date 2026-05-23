-- 添加 next_change 字段到 limit_up_stocks 表
ALTER TABLE limit_up_stocks ADD COLUMN IF NOT EXISTS next_change NUMERIC(10, 4);

-- 添加注释
COMMENT ON COLUMN limit_up_stocks.next_change IS '次日涨跌幅(%)';
