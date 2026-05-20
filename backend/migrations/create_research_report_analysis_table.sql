-- 创建研报AI分析结果缓存表
CREATE TABLE IF NOT EXISTS research_report_analysis_results (
    id SERIAL PRIMARY KEY,
    info_code VARCHAR(50) NOT NULL,
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

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_research_report_code ON research_report_analysis_results(stock_code);
CREATE INDEX IF NOT EXISTS idx_research_report_date ON research_report_analysis_results(analysis_date);

-- 添加注释
COMMENT ON TABLE research_report_analysis_results IS '研报AI分析结果缓存表';
COMMENT ON COLUMN research_report_analysis_results.info_code IS '研报ID';
COMMENT ON COLUMN research_report_analysis_results.stock_code IS '股票代码';
COMMENT ON COLUMN research_report_analysis_results.stock_name IS '股票名称';
COMMENT ON COLUMN research_report_analysis_results.title IS '研报标题';
COMMENT ON COLUMN research_report_analysis_results.rating IS '机构评级';
COMMENT ON COLUMN research_report_analysis_results.rating_change IS '评级变化';
COMMENT ON COLUMN research_report_analysis_results.analysis_result IS 'AI分析结果(JSON格式)';
COMMENT ON COLUMN research_report_analysis_results.analysis_date IS '分析日期';

-- 迁移旧数据（如果有的话）
-- 将 ai_analysis_results 表中以 'REPORT_' 开头的研报分析数据迁移到新表
INSERT INTO research_report_analysis_results (
    info_code, 
    stock_code, 
    stock_name, 
    title, 
    rating, 
    rating_change, 
    analysis_result, 
    analysis_date, 
    created_at, 
    updated_at
)
SELECT 
    REPLACE(stock_code, 'REPORT_', '') as info_code,
    stock_code as stock_code,
    stock_name,
    stock_name as title,
    NULL as rating,
    NULL as rating_change,
    analysis_result,
    trade_date as analysis_date,
    created_at,
    updated_at
FROM ai_analysis_results
WHERE stock_code LIKE 'REPORT_%'
ON CONFLICT (info_code) DO NOTHING;

-- 删除已迁移的旧数据
DELETE FROM ai_analysis_results WHERE stock_code LIKE 'REPORT_%';
