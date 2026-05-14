-- 修改 ai_analysis_results 表的 stock_name 字段长度
ALTER TABLE ai_analysis_results ALTER COLUMN stock_name TYPE VARCHAR(500);
