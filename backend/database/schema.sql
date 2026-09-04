-- 个人复盘网站数据库设计
-- 注意：在 docker 部署中，postgres 镜像会用 POSTGRES_DB 环境变量自动创建数据库，
-- 并自动在 <POSTGRES_DB> 库中执行本脚本。因此这里不能重复 CREATE DATABASE，
-- 否则初始化会因 "database already exists" 冲突而被整体跳过。
-- 如需在本地手动初始化，可自行执行：
--   psql -U postgres -c 'CREATE DATABASE stock_review;'
--   psql -U postgres -d stock_review -f schema.sql

-- 1. 板块表
CREATE TABLE blocks (
    id SERIAL PRIMARY KEY,
    block_code VARCHAR(20) NOT NULL,
    block_name VARCHAR(100) NOT NULL,
    trade_date DATE NOT NULL,
    change_rate DECIMAL(10, 4),
    limit_up_num INTEGER DEFAULT 0,
    continuous_plate_num INTEGER DEFAULT 0,
    high VARCHAR(20),
    high_num INTEGER DEFAULT 0,
    list_days INTEGER DEFAULT 0,
    high_stock_code VARCHAR(10),
    high_stock_name VARCHAR(50),
    stock_codes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_block_date UNIQUE (block_code, trade_date)
);

-- 创建板块表索引
CREATE INDEX idx_blocks_date ON blocks(trade_date);
CREATE INDEX idx_blocks_code ON blocks(block_code);
CREATE INDEX idx_blocks_name ON blocks(block_name);
CREATE INDEX idx_blocks_limit_num ON blocks(limit_up_num);
CREATE INDEX idx_blocks_continuous_num ON blocks(continuous_plate_num);

COMMENT ON TABLE blocks IS '板块表';

-- 概念板块全量维表（由 scripts/fetch_dim_blocks.py 维护，筛选/概念匹配用）
CREATE TABLE IF NOT EXISTS dim_block (
    plate_code TEXT PRIMARY KEY,
    plate_name TEXT NOT NULL,
    board_type TEXT NOT NULL DEFAULT 'concept',
    change_pct DOUBLE PRECISION,
    updated_at TIMESTAMP DEFAULT now()
);
COMMENT ON TABLE dim_block IS '概念板块全量维表';

-- 2. 涨停股票表
CREATE TABLE limit_up_stocks (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    trade_date DATE NOT NULL,
    limit_up_reason VARCHAR(200),
    limit_up_time TIME,
    limit_up_price DECIMAL(10, 2),
    limit_up_type VARCHAR(20),
    block_id INTEGER REFERENCES blocks(id),
    ths_reason_info TEXT,
    seal_amount DECIMAL(15, 2),
    continuous_days INTEGER DEFAULT 1,
    high_days VARCHAR(20),
    sector VARCHAR(50),
    change_percent DECIMAL(10, 4),
    turnover_rate DECIMAL(10, 4),
    amount DECIMAL(20, 2),
    is_high_stock INTEGER DEFAULT 0,
    next_change DECIMAL(10, 4),
    next_open_change DECIMAL(10, 4),
    current_status VARCHAR(20) DEFAULT 'close',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stock_date UNIQUE (stock_code, trade_date)
);

-- 3. 连板天梯统计表
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

-- 4. 数据抓取日志表
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
CREATE INDEX idx_stocks_date_days ON limit_up_stocks(trade_date, continuous_days);
CREATE INDEX idx_stocks_date_time ON limit_up_stocks(trade_date, limit_up_time);
CREATE INDEX idx_stocks_block_id ON limit_up_stocks(block_id);
CREATE INDEX idx_stocks_reason ON limit_up_stocks(limit_up_reason);
CREATE INDEX idx_stocks_change ON limit_up_stocks(change_percent);
CREATE INDEX idx_stocks_seal ON limit_up_stocks(seal_amount);
CREATE INDEX idx_stocks_sector ON limit_up_stocks(sector);

CREATE INDEX idx_ladder_date ON ladder_stats(trade_date);

CREATE INDEX idx_logs_date ON fetch_logs(fetch_date);
CREATE INDEX idx_logs_status ON fetch_logs(status);
CREATE INDEX idx_logs_time ON fetch_logs(fetch_time);

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
    login_count INTEGER DEFAULT 0,
    last_login TIMESTAMP,
    last_activity TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_username UNIQUE (username),
    CONSTRAINT uq_user_email UNIQUE (email)
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
COMMENT ON COLUMN users.login_count IS '登录次数';
COMMENT ON COLUMN users.last_login IS '最后登录时间';
COMMENT ON COLUMN users.last_activity IS '最后活动时间';

-- 自选股表
CREATE TABLE watchlist_stocks (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    add_date DATE NOT NULL,
    add_price DECIMAL(10, 2),
    alert_price DECIMAL(10, 2),
    signal_date DATE,
    add_reason VARCHAR(200),
    source VARCHAR(50),
    add_type VARCHAR(20) DEFAULT 'manual',
    limit_up_reason_category VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_watchlist_stock UNIQUE (user_id, stock_code)
);

CREATE INDEX idx_watchlist_user_id ON watchlist_stocks(user_id);
CREATE INDEX idx_watchlist_created ON watchlist_stocks(created_at);

COMMENT ON TABLE watchlist_stocks IS '自选股表';

-- 自选股入选原因向量库（持久化，bge-small-zh 512 维；自选股向量搜索用）
CREATE TABLE IF NOT EXISTS watchlist_reason_vectors (
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    stock_code VARCHAR(10) NOT NULL,
    reason_text TEXT NOT NULL,
    embedding DOUBLE PRECISION[] NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, stock_code)
);
CREATE INDEX IF NOT EXISTS idx_wrvec_user ON watchlist_reason_vectors(user_id);
COMMENT ON TABLE watchlist_reason_vectors IS '自选股入选原因向量库';

-- 交易记录表
CREATE TABLE trade_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    operation_type VARCHAR(10) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    buy_price DECIMAL(10, 2),
    quantity INTEGER NOT NULL,
    remaining_quantity INTEGER DEFAULT 0,
    amount DECIMAL(12, 2),
    profit DECIMAL(10, 2),
    profit_ratio DECIMAL(10, 4),
    operation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trade_records_user_id ON trade_records(user_id);
CREATE INDEX idx_trade_records_date ON trade_records(operation_date);

COMMENT ON TABLE trade_records IS '交易记录表';

-- AI分析结果缓存表
CREATE TABLE ai_analysis_results (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(50) NOT NULL,
    stock_name VARCHAR(500) NOT NULL,
    trade_date DATE NOT NULL,
    analysis_result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ai_analysis_stock_date UNIQUE (stock_code, trade_date)
);

CREATE INDEX idx_ai_analysis_date ON ai_analysis_results(trade_date);
CREATE INDEX idx_ai_analysis_code ON ai_analysis_results(stock_code);

COMMENT ON TABLE ai_analysis_results IS 'AI分析结果缓存表';

-- 自选股AI分析结果缓存表
CREATE TABLE watchlist_analysis_results (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(50) NOT NULL,
    stock_name VARCHAR(500) NOT NULL,
    analysis_date DATE NOT NULL,
    analysis_result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_watchlist_analysis_stock_date UNIQUE (stock_code, analysis_date)
);

CREATE INDEX idx_watchlist_analysis_date ON watchlist_analysis_results(analysis_date);
CREATE INDEX idx_watchlist_analysis_code ON watchlist_analysis_results(stock_code);

COMMENT ON TABLE watchlist_analysis_results IS '自选股AI分析结果缓存表';

-- 研报AI分析结果缓存表
CREATE TABLE research_report_analysis_results (
    id SERIAL PRIMARY KEY,
    info_code VARCHAR(50) NOT NULL UNIQUE,
    stock_code VARCHAR(50) NOT NULL,
    stock_name VARCHAR(500) NOT NULL,
    title VARCHAR(500) NOT NULL,
    rating VARCHAR(50),
    rating_change VARCHAR(50),
    analysis_result TEXT NOT NULL,
    analysis_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_research_report_info_code UNIQUE (info_code)
);

CREATE INDEX idx_research_report_code ON research_report_analysis_results(stock_code);
CREATE INDEX idx_research_report_date ON research_report_analysis_results(analysis_date);

COMMENT ON TABLE research_report_analysis_results IS '研报AI分析结果缓存表';

-- 热门话题AI分析结果缓存表
CREATE TABLE hot_topic_analysis_results (
    id SERIAL PRIMARY KEY,
    topic_title VARCHAR(500) NOT NULL UNIQUE,
    analysis_result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_hot_topic_title UNIQUE (topic_title)
);

CREATE INDEX idx_hot_topic_title ON hot_topic_analysis_results(topic_title);

COMMENT ON TABLE hot_topic_analysis_results IS '热门话题AI分析结果缓存表';

-- 财联社新闻表
CREATE TABLE cls_news (
    id SERIAL PRIMARY KEY,
    news_id VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500),
    content TEXT,
    ctime TIMESTAMP NOT NULL,
    is_important INTEGER DEFAULT 0,
    has_stocks INTEGER DEFAULT 0,
    confirmed INTEGER DEFAULT 0,
    reading_num INTEGER DEFAULT 0,
    stock_list TEXT,
    analysis_result TEXT,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cls_news_id ON cls_news(news_id);
CREATE INDEX idx_cls_news_ctime ON cls_news(ctime);
CREATE INDEX idx_cls_news_important ON cls_news(is_important);

COMMENT ON TABLE cls_news IS '财联社新闻表';

-- 用户策略表
CREATE TABLE user_strategies (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) DEFAULT 'custom',
    query_template TEXT NOT NULL,
    description VARCHAR(500),
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategy_user_id ON user_strategies(user_id);
CREATE INDEX idx_strategy_type ON user_strategies(strategy_type);
CREATE INDEX idx_strategy_is_default ON user_strategies(is_default);

COMMENT ON TABLE user_strategies IS '用户策略表';

-- 市场动态消息表
CREATE TABLE market_alerts (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    continuous_days INTEGER DEFAULT 1,
    alert_time VARCHAR(10),
    alert_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_stock_alert UNIQUE (stock_code, alert_type)
);

-- 创建索引
CREATE INDEX idx_alerts_trade_date ON market_alerts(trade_date);
CREATE INDEX idx_alerts_stock_code ON market_alerts(stock_code);
CREATE INDEX idx_alerts_created_at ON market_alerts(created_at);

-- 表注释
COMMENT ON TABLE market_alerts IS '市场动态消息表';
COMMENT ON COLUMN market_alerts.alert_type IS '告警类型(limit_up/break板/回封)';
COMMENT ON COLUMN market_alerts.status IS '状态(close/open/new/reclose)';

-- 关键词归并分析缓存表（每日涨停关键词归并分析结果）
CREATE TABLE IF NOT EXISTS keyword_analysis (
    id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    raw_keywords TEXT,
    merged_keywords TEXT,
    analysis_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_keyword_analysis_trade_date UNIQUE (trade_date)
);
COMMENT ON TABLE keyword_analysis IS '每日涨停关键词归并分析缓存';

-- 每日自动筛选配置表（每策略一个开关：user_id + strategy）
CREATE TABLE IF NOT EXISTS auto_screening_config (
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    strategy VARCHAR(20) NOT NULL DEFAULT 'bottom',
    enabled INTEGER NOT NULL DEFAULT 0,
    params TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, strategy)
);
COMMENT ON TABLE auto_screening_config IS '每日19:00自动筛选开关配置（按策略）';

-- 每日自动筛选执行日志表
CREATE TABLE IF NOT EXISTS auto_screening_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(uid),
    strategy VARCHAR(20) NOT NULL DEFAULT 'bottom',  -- bottom=抄底放量 / breakout=突破放量
    run_date DATE NOT NULL,
    added_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_auto_screening_user_date
    ON auto_screening_logs (user_id, run_date);
CREATE INDEX IF NOT EXISTS idx_auto_screening_user_strategy_date
    ON auto_screening_logs (user_id, strategy, run_date);
COMMENT ON TABLE auto_screening_logs IS '每日自动筛选执行日志（按策略隔离）';
