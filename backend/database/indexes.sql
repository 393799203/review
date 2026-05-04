-- 数据库索引优化脚本
-- 用于提升大数据量下的查询性能

-- =====================
-- limit_up_stocks 表索引
-- =====================

-- 复合索引：按日期和连板数查询（最常用的查询场景）
CREATE INDEX IF NOT EXISTS idx_stocks_date_days ON limit_up_stocks(trade_date, continuous_days);

-- 复合索引：按日期和涨停时间排序
CREATE INDEX IF NOT EXISTS idx_stocks_date_time ON limit_up_stocks(trade_date, limit_up_time);

-- 板块ID索引：按板块查询股票
CREATE INDEX IF NOT EXISTS idx_stocks_block_id ON limit_up_stocks(block_id);

-- 涨停原因索引：按涨停原因模糊查询
CREATE INDEX IF NOT EXISTS idx_stocks_reason ON limit_up_stocks(limit_up_reason);

-- 涨跌幅索引：按涨幅排序
CREATE INDEX IF NOT EXISTS idx_stocks_change ON limit_up_stocks(change_percent);

-- 封单量索引：按封单量排序
CREATE INDEX IF NOT EXISTS idx_stocks_seal ON limit_up_stocks(seal_amount);

-- 所属板块索引：按板块筛选
CREATE INDEX IF NOT EXISTS idx_stocks_sector ON limit_up_stocks(sector);

-- =====================
-- blocks 表索引
-- =====================

-- 交易日期索引
CREATE INDEX IF NOT EXISTS idx_blocks_date ON blocks(trade_date);

-- 板块代码索引
CREATE INDEX IF NOT EXISTS idx_blocks_code ON blocks(block_code);

-- 板块名称索引
CREATE INDEX IF NOT EXISTS idx_blocks_name ON blocks(block_name);

-- 涨停家数索引：按热度排序
CREATE INDEX IF NOT EXISTS idx_blocks_limit_num ON blocks(limit_up_num DESC);

-- 连板家数索引
CREATE INDEX IF NOT EXISTS idx_blocks_continuous_num ON blocks(continuous_plate_num DESC);

-- =====================
-- fetch_logs 表索引
-- =====================

-- 抓取日期索引
CREATE INDEX IF NOT EXISTS idx_logs_date ON fetch_logs(fetch_date);

-- 状态索引：按状态筛选
CREATE INDEX IF NOT EXISTS idx_logs_status ON fetch_logs(status);

-- 抓取时间索引：按时间排序
CREATE INDEX IF NOT EXISTS idx_logs_time ON fetch_logs(fetch_time);

-- =====================
-- ladder_stats 表索引
-- =====================

-- 交易日期索引（已存在unique约束，无需额外创建）

-- =====================
-- 分析查询性能
-- =====================

-- 查看索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 查看表大小
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
