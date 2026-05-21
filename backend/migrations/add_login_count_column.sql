-- 添加login_count字段到users表
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- 为现有用户初始化login_count为0
UPDATE users SET login_count = 0 WHERE login_count IS NULL;
