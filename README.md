# 个人复盘网站 - 涨停天梯

一个专业的个人复盘网站，用于追踪和分析A股涨停股票的连板天梯情况。

## ✨ 功能特色

- 🎯 **连板天梯分析**: 自动识别和分类连板股票（首板至8连板及以上）
- 📊 **详细数据展示**: 涨停原因、涨停时间、收盘封单量等完整信息
- 💾 **数据库存储**: PostgreSQL数据库，数据持久化
- 🌐 **Web界面**: 美观易用的前端界面
- 📅 **日期切换**: 查看最近5个交易日的历史数据
- 🔍 **数据筛选**: 按连板天数分类查看

## 🚀 快速开始

### 1. 安装PostgreSQL

**macOS**:

```bash
brew install postgresql
brew services start postgresql
```

**Linux**:

```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. 创建数据库

```bash
# 方法1：使用createdb命令
createdb stock_review

# 方法2：使用psql
psql -U postgres
CREATE DATABASE stock_review;
\q
```

### 3. 配置数据库连接

编辑 `.env` 文件，修改数据库连接信息：

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_review
DB_USER=postgres
DB_PASSWORD=你的密码
```

## 4. 启动应用

```bash
./start.sh
```

脚本会自动：

- ✅ 安装依赖包
- ✅ 初始化数据库表
- ✅ 询问是否爬取数据
- ✅ 启动Web服务

### 5. 访问Web界面

打开浏览器访问：`http://localhost:5000`

## 📊 使用说明

### Web界面

- **自动加载**: 打开网站自动加载最新交易日数据
- **标签页切换**: 点击标签页查看不同连板梯队
- **日期切换**: 使用日期选择器查看历史数据
- **数据统计**: 实时显示涨停股票统计信息

### 数据字段说明

每只涨停股票显示以下信息：

| 字段    | 说明            |
| ----- | ------------- |
| 代码    | 股票代码          |
| 名称    | 股票名称          |
| 涨停原因  | 涨停的具体原因（行业分类） |
| 涨停时间  | 最后封板时间        |
| 收盘封单量 | 收盘时的封单资金（万元）  |
| 所属板块  | 科创板、创业板、沪深A股等 |
| 涨幅    | 当日涨幅百分比       |
| 换手率   | 当日换手率         |

### 数据爬取

```bash
# 爬取最近5个交易日
python3 fetch_data.py --recent 5

# 爬取指定日期
python3 fetch_data.py --date 20260501
```

## 🔧 API接口

### 1. 健康检查

```
GET /api/health
```

### 2. 获取所有可用日期

```
GET /api/dates
```

### 3. 获取最新交易日

```
GET /api/latest
```

### 4. 获取指定日期连板天梯

```
GET /api/ladder/<date_str>
```

示例：`GET /api/ladder/20260501`

### 5. 获取统计数据

```
GET /api/statistics/<date_str>
```

示例：`GET /api/statistics/20260501`

## 💾 数据库管理

### 查看数据

```bash
psql -U postgres -d stock_review

# 查看涨停股票
SELECT * FROM limit_up_stocks WHERE trade_date = '2026-05-01' LIMIT 10;

# 查看统计
SELECT * FROM ladder_stats ORDER BY trade_date DESC;

# 查看抓取日志
SELECT * FROM fetch_logs ORDER BY fetch_time DESC LIMIT 10;
```

### 数据备份

```bash
pg_dump -U postgres stock_review > backup.sql
```

### 数据恢复

```bash
psql -U postgres stock_review < backup.sql
```

## ⏰ 定时任务

设置每天下午3点半自动爬取：

```bash
crontab -e

# 添加以下行
30 15 * * * cd /Users/dingyuebo/projects/stock/review && /usr/bin/python3 fetch_data.py --recent 1 >> /tmp/stock_review.log 2>&1
```

## 📁 项目结构

```
review/
├── app.py              # Flask应用主文件
├── models.py           # 数据库模型
├── fetch_data.py       # 数据爬取脚本
├── templates/
│   └── index.html      # 前端页面
├── database/
│   └── schema.sql      # 数据库建表SQL
├── .env                # 环境配置
├── requirements.txt    # Python依赖
├── start.sh            # 启动脚本
└── README.md           # 项目说明
```

## 🔍 故障排查

### 问题1：数据库连接失败

**解决方法**：

1. 确认PostgreSQL服务已启动
2. 检查 `.env` 文件中的连接信息
3. 确认数据库已创建

### 问题2：端口被占用

**解决方法**：

```bash
# 查看端口占用
lsof -i :5000

# 杀掉进程
kill -9 <PID>
```

### 问题3：数据爬取失败

**解决方法**：

1. 检查网络连接
2. 确认日期是交易日
3. 查看错误日志

## 💡 使用建议

1. **首次使用**: 运行 `./start.sh` 完成初始化
2. **日常使用**: 每天收盘后运行爬取脚本更新数据
3. **数据分析**: 使用Web界面查看和分析数据
4. **数据备份**: 定期备份PostgreSQL数据库

## 📝 更新日志

### v1.0.0 (2026-05-02)

- ✨ 初始版本发布
- 🎯 支持涨停天梯数据获取
- 📊 完整的数据展示功能
- 💾 PostgreSQL数据库存储
- 🌐 Web界面访问

***

**立即运行** **`./start.sh`** **开始使用！** 🚀
