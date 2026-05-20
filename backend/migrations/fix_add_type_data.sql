-- 修复 add_type 字段数据
-- 除了歌尔股份其他都是策略加入

-- 更新歌尔股份为手动加入
UPDATE watchlist_stocks 
SET add_type = 'manual'
WHERE stock_name LIKE '%歌尔%';

-- 更新其他股票为策略加入
UPDATE watchlist_stocks 
SET add_type = 'strategy'
WHERE stock_name NOT LIKE '%歌尔%';
