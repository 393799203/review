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

-- 用户表
CREATE TABLE users (
    uid VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::VARCHAR(36),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50),
    avatar VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    is_vip INTEGER DEFAULT 0,
    vip_expire_date DATE,
    settings TEXT,
    is_active INTEGER DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户表索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- 用户表注释
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.uid IS '用户UID';
COMMENT ON COLUMN users.username IS '用户名';
COMMENT ON COLUMN users.email IS '邮箱';
COMMENT ON COLUMN users.password_hash IS '密码哈希';
COMMENT ON COLUMN users.nickname IS '昵称';
COMMENT ON COLUMN users.avatar IS '头像URL';
COMMENT ON COLUMN users.role IS '角色（user:普通用户, admin:管理员, vip:VIP用户）';
COMMENT ON COLUMN users.is_vip IS '是否为VIP（0:否, 1:是）';
COMMENT ON COLUMN users.vip_expire_date IS 'VIP到期日期';
COMMENT ON COLUMN users.settings IS '用户设置JSON';
COMMENT ON COLUMN users.is_active IS '是否激活（1:激活，0:未激活）';
COMMENT ON COLUMN users.last_login IS '最后登录时间';
