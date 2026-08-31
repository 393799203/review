# 后端目录结构说明

## 📁 目录结构

```
backend/
├── app/                    # 应用主目录（分层架构）
│   ├── controllers/        # 控制器层
│   ├── services/          # 服务层
│   ├── repositories/      # 数据访问层
│   └── utils/             # 工具类
├── core/                  # 核心服务模块
│   ├── data_fetcher.py    # 数据获取器
│   ├── fetch_data.py      # 涨停数据抓取
│   ├── limit_up_analyzer.py  # 涨停原因分析
│   ├── statistics_api.py  # 统计API
│   ├── trade_calendar.py  # 交易日历
│   ├── wencai_fetcher.py  # 问财数据获取
│   ├── email_utils.py     # 邮件工具
│   └── quotes_utils.py    # 行情工具
├── database/              # 数据库相关
│   ├── schema.sql        # 数据库结构
│   └── indexes.sql       # 索引定义
├── static/                # 静态文件
├── templates/             # 模板文件
├── app.py                 # 应用入口
├── models.py              # 数据模型
├── database.py            # 数据库配置
└── requirements.txt       # 依赖包
```

## 🏗️ 架构说明

### 分层架构
- **Controller层**：处理HTTP请求，参数验证，调用Service层
- **Service层**：业务逻辑处理，调用Repository层
- **Repository层**：数据访问，数据库操作

### 核心服务模块 (core/)
所有底层服务统一放在 `core/` 目录下，包括：
- 数据获取服务
- 分析服务
- 工具类服务

## 📝 导入规则

### 从core模块导入
```python
# 正确的导入方式
from core.data_fetcher import DataFetcher
from core.trade_calendar import TradeCalendar
from core.wencai_fetcher import WencaiFetcher
from core.limit_up_analyzer import LimitUpReasonAnalyzer
from core.statistics_api import register_statistics_routes
from core.email_utils import send_welcome_email_to_user
from core.quotes_utils import get_realtime_quotes
```

### 从app模块导入
```python
# 控制器
from app.controllers.auth_controller import auth_controller

# 服务
from app.services.ladder_service import LadderService

# 仓库
from app.repositories.stock_repository import StockRepository
```

## 🔄 重构历史

### 已完成
- ✅ 将单体应用重构为分层架构
- ✅ 整理底层服务到 `core/` 目录
- ✅ 删除旧的单体应用文件
- ✅ 统一导入路径

### 已删除
- ❌ `old_app/app.py` - 旧的单体应用
- ❌ `check_db.py` - 数据库检查脚本
- ❌ `migrations/` - 数据库迁移脚本（已迁移完成）

## 🚀 部署说明

### 本地开发
```bash
cd backend
python3 app.py
```

### Docker部署
```bash
docker compose up -d
```

## 📚 相关文档

- [API文档](./API.md)
- [数据库设计](./database/README.md)
- [部署指南](../deploy/README.md)

## 📈 量化筛选模块（screening）

新增"量化筛选"功能，查询外部 TDX 行情库（PostgreSQL，schema=tdx，只读）：

- `app/core/tdx_db.py` - TDX 库连接（懒加载单例 engine，小连接池，只读）
- `app/repositories/screening_repository.py` - 筛选 SQL（窗口函数实现）
- `app/services/screening_service.py` - 参数校验与筛选公式说明（docstring）
- `app/controllers/screening_controller.py` - 接口控制器

接口（均需登录）：

- `GET /api/screening/dates` - 最近有数据的交易日列表
- `POST /api/screening/run` - 执行筛选，支持 `strategy` 参数切换策略：
  - `bottom`（默认，抄底放量）：D 向前连续 3 日逐日放量校验
    （第 1 天 ≥ 均量×day1_mult，第 2/3 天 ≥ 均量×day23_mult，vol_window 默认 20）
  - `breakout`（突破放量）：高换手 + 短上影 + 放量突破 N 日前高 + 不过度追高

### 配置

需要在 `review/.env` 中自行添加 TDX 行情库连接串（不配置时接口返回 503）：

```
TDX_DATABASE_URL=postgresql://user:pass@host:5432/quantdb
```

依赖表/视图：`tdx.raw_stocks_daily`、`tdx.raw_stocks_basic`、
`tdx.dim_sw_industry`、`tdx.v_sw_industry_daily`。

## 🤖 策略代码生成模块（strategy-gen）

用户输入自然语言选股/量化条件，调用 DeepSeek 生成自包含可运行的 Python
策略脚本（psycopg2 + pandas，读 TDX 行情库，连接串从脚本环境变量 `DB_URL` 读取）：

- `app/services/strategy_gen_service.py` - prompt 构建与代码提取（数据环境说明固定在 system prompt）
- `app/controllers/strategy_gen_controller.py` - 接口控制器

接口（需登录）：

- `POST /api/strategy-gen/generate` - 入参 `{ requirement, with_backtest }`，
  出参 `{ code, model }`；未配置 `DEEPSEEK_API_KEY` 时返回 503。

**安全说明：服务端只生成代码文本，不执行任何生成的代码**；
生成的脚本由用户下载后在本地自行运行（需 `pip install psycopg2-binary pandas`
并设置 `DB_URL`）。
