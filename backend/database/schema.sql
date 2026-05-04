-- 个人复盘网站数据库设计

-- 创建数据库
CREATE DATABASE stock_review;

-- 连接到数据库
\c stock_review;

-- 1. 涨停股票表
CREATE TABLE limit_up_stocks (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    trade_date DATE NOT NULL,
    limit_up_reason VARCHAR(200),
    limit_up_time TIME,
    seal_amount DECIMAL(15, 2),
    continuous_days INTEGER DEFAULT 1,
    sector VARCHAR(50),
    change_percent DECIMAL(10, 4),
    turnover_rate DECIMAL(10, 4),
    amount DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

-- 2. 连板天梯统计表
CREATE TABLE ladder_stats (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    total_count INTEGER DEFAULT 0,
    first_board INTEGER DEFAULT 0,
    second_board INTEGER DEFAULT 0,
    third_board INTEGER DEFAULT 0,
    fourth_board INTEGER DEFAULT 0,
    fifth_board INTEGER DEFAULT 0,
    sixth_board INTEGER DEFAULT 0,
    seventh_board INTEGER DEFAULT 0,
    eighth_plus_board INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 数据抓取日志表
CREATE TABLE fetch_logs (
    id SERIAL PRIMARY KEY,
    fetch_date DATE NOT NULL,
    fetch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    stocks_count INTEGER DEFAULT 0,
    error_message TEXT,
    duration_seconds INTEGER
);

-- 创建索引
CREATE INDEX idx_stocks_date ON limit_up_stocks(trade_date);
CREATE INDEX idx_stocks_code ON limit_up_stocks(stock_code);
CREATE INDEX idx_stocks_days ON limit_up_stocks(continuous_days);
CREATE INDEX idx_ladder_date ON ladder_stats(trade_date);

-- 创建视图：连板天梯视图
CREATE VIEW v_ladder AS
SELECT 
    trade_date,
    continuous_days,
    COUNT(*) as stock_count,
    array_agg(stock_code ORDER BY seal_amount DESC) as stock_codes,
    array_agg(stock_name ORDER BY seal_amount DESC) as stock_names,
    array_agg(limit_up_reason ORDER BY seal_amount DESC) as reasons
FROM limit_up_stocks
GROUP BY trade_date, continuous_days
ORDER BY trade_date DESC, continuous_days;

-- 创建视图：每日统计视图
CREATE VIEW v_daily_stats AS
SELECT 
    trade_date,
    COUNT(*) as total_stocks,
    COUNT(CASE WHEN continuous_days = 1 THEN 1 END) as first_board,
    COUNT(CASE WHEN continuous_days = 2 THEN 1 END) as second_board,
    COUNT(CASE WHEN continuous_days = 3 THEN 1 END) as third_board,
    COUNT(CASE WHEN continuous_days = 4 THEN 1 END) as fourth_board,
    COUNT(CASE WHEN continuous_days >= 5 THEN 1 END) as fifth_plus_board
FROM limit_up_stocks
GROUP BY trade_date
ORDER BY trade_date DESC;

-- 注释
COMMENT ON TABLE limit_up_stocks IS '涨停股票表';
COMMENT ON COLUMN limit_up_stocks.limit_up_reason IS '涨停原因';
COMMENT ON COLUMN limit_up_stocks.limit_up_time IS '涨停时间';
COMMENT ON COLUMN limit_up_stocks.seal_amount IS '收盘封单量（元）';
COMMENT ON COLUMN limit_up_stocks.continuous_days IS '连续涨停天数';
