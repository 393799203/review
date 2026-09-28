# stock-review 部署文档

> 涨停天梯·复盘系统（Flask 后端 + React 前端 + PostgreSQL），已部署于：
> - 新服务器 `124.221.228.215`（ubuntu，当前主力）
> - 旧服务器 `192.168.110.115`（root，备份，仍在线）
>
> 部署目录：`/opt/stock-review/`，TDX 行情数据：`/opt/TDX_daily/`

## 1. 架构

| 服务 | 容器/镜像 | 端口 | 说明 |
|---|---|---|---|
| frontend | nginx:alpine | 80 | 挂载 `frontend/dist`（本地 vite build 产物），nginx 代理 `/api` → backend |
| backend | 自建镜像（./backend） | 5001 | Flask API，内置每日 19:00 自动筛选调度 |
| db | postgres:15-alpine | 127.0.0.1:5432 | `stock_review` 库（业务）+ `quantdb` 库（TDX 行情） |
| tdx-daily | 自建镜像（tdx_daily/） | — | 按 cron 从官网下载日线导入 quantdb（--rm 临时容器） |

## 2. 前置条件

- 服务器：≥2GB 内存（1.9G 已很紧张）、≥20GB 磁盘、装好 Docker + Docker Compose
- 域名：解析到服务器 IP；**国内服务器必须 ICP 备案**，否则域名被腾讯云 302 拦截（`dnspod.qcloud.com/static/webblock.html`），备案前只能用 IP 访问
- 本地构建前端：`cd frontend && npm run build`（产物 `frontend/dist` 随 rsync 上传）

## 3. 全新部署步骤

### 3.1 同步代码

```bash
rsync -az -e "ssh -i ~/.ssh/id_rsa" --exclude=.git --exclude=.venv \
  --exclude=backend/__pycache__ --exclude=embed-cache \
  review/ ubuntu@124.221.228.215:/opt/stock-review/
```

### 3.2 配置 .env

```bash
cp .env.example .env   # 填写全部密钥
```

关键项（详见 `.env.example` 注释）：
- `DB_PASSWORD` 必须与 compose 中 db 硬编码密码一致（默认 `stock2024`，compose 已有默认值，缺省也行）
- `DEEPSEEK_API_URL/MODEL/MODELS` 有默认值；`DEEPSEEK_API_KEY` 必填（账户欠费会 402）
  - 当前生产走 wasu 网关：`DEEPSEEK_API_URL=https://token.wasu.cn/v1/chat/completions`、`DEEPSEEK_MODEL=deepseek-v4.1-flash`
  - **注意 host 是 `token.wasu.cn`**（OpenAI 兼容 tokenhub）；`api.wasu.cn` 不是 AI 入口，所有路径均 404
  - URL 必须是**完整端点**（到 `/chat/completions`），因为 `ai_service` / `limit_up_analyzer` 直接 POST 该值
  - 模型名以 `GET https://token.wasu.cn/v1/models` 返回为准（该网关无 `deepseek-v1-flash`）
- `DEEPSEEK_MAX_TOKENS_*` 用时务必确认在**容器内**生效（`docker exec stock-review-backend-1 env | grep DEEPSEEK_MAX`），
  compose 写死会覆盖 .env；推理模型预算不足会导致 AI 分析“返回空正文”而失败
- `TDX_DATABASE_URL=postgresql://stock_user:<密码>@db:5432/quantdb`（量化筛选用，缺省时筛选返回 503 提示）

### 3.3 启动

```bash
cd /opt/stock-review && docker compose up -d --build
```

- DB 首次初始化自动执行 `backend/database/schema.sql`，建全 **18 张表**（含 dim_block / keyword_analysis / auto_screening_*）
- ⚠️ schema.sql 内**不要**加 `CREATE DATABASE`（POSTGRES_DB 已建库，加了会导致初始化被跳过）

### 3.4 验证

```bash
curl http://localhost/api/health            # {"status":"ok",...}
curl -I http://localhost/                    # 200
docker exec stock-review-db-1 psql -U stock_user -d stock_review -c "\dt"
```

## 4. TDX 行情库（tdx_daily）部署

### 4.1 建 quantdb 库

```bash
docker exec stock-review-db-1 psql -U stock_user -d postgres -c "CREATE DATABASE quantdb;"
```

### 4.2 配置 + 构建镜像

```bash
echo "DB_URL=postgresql://stock_user:<密码>@127.0.0.1:5432/quantdb" > /opt/stock-review/tdx_daily/.env
cd /opt/stock-review/tdx_daily && docker build -t tdx-daily .
```

### 4.3 首次灌库（二选一）

**A. 从旧服务器迁移已下载的 vipdoc 缓存（推荐，快）**
```bash
# 旧服务器 → 本地 → 新服务器 中转（新服务器无法直连旧服务器内网）
rsync -az -e "ssh -i ~/.ssh/id_rsa" root@192.168.110.115:/opt/TDX_daily/cache/web_daily/vipdoc/ /tmp/tdx_vipdoc/
rsync -az -e "ssh -i ~/.ssh/id_rsa" /tmp/tdx_vipdoc/ ubuntu@124.221.228.215:/opt/TDX_daily/cache/web_daily/vipdoc/
```

**B. 从官网逐日下载（无需旧数据）**
```bash
bash /opt/stock-review/tdx_daily/deploy/backfill.sh 2025-09-01 2026-09-01
```

然后导入（日线 + GBBQ + 因子 + 复权/申万视图）：
```bash
docker run --rm --network host --env-file /opt/stock-review/tdx_daily/.env \
  -v /opt/TDX_daily/cache:/app/.cache \
  tdx-daily python -u run_daily.py --lday-path /app/.cache/web_daily/vipdoc \
  --min-date 2025-09-01 --full-basic --full-factor
docker run --rm --network host --env-file /opt/stock-review/tdx_daily/.env \
  tdx-daily python import_sw_industry_standalone.py
docker run --rm --network host --env-file /opt/stock-review/tdx_daily/.env \
  tdx-daily python create_sw_views_standalone.py
```

### 4.4 每日增量 cron

`daily_run.sh`（已就位）：
```bash
docker run --rm --network host --env-file /opt/stock-review/tdx_daily/.env \
  -v /opt/TDX_daily/cache:/app/.cache -v /opt/TDX_daily/logs:/app/logs \
  tdx-daily python -u run_daily.py --download-daily --recent-days 10 \
  >> /opt/TDX_daily/logs/cron.log 2>&1
```

安装（周一至五 18:03，对齐旧服务器）：
```bash
(crontab -l 2>/dev/null | grep -v "tdx_daily\|tdx-daily"; \
 echo "3 18 * * 1-5 /opt/stock-review/tdx_daily/daily_run.sh") | crontab -
```

## 5. 数据迁移（从旧服务器）

用户/业务数据迁移（本次实操验证）：
1. 表对比：`SELECT tablename FROM pg_tables WHERE schemaname='public'`，两库差集补建
2. 导出：`COPY <表> TO STDOUT WITH CSV HEADER`
3. 导入：列序一致直接 `COPY <表> FROM '<csv>' WITH CSV HEADER`；列序不一致用 Python 按列名 INSERT（见本次经验：users 列序差异 + settings 空值处理）

已迁移清单：users(4)、blocks(1391)、dim_block(417)、watchlist_stocks(629)、user_strategies(1)、trade_records(2)、auto_screening_config(3)、auto_screening_logs(3)、ladder_stats(46)、limit_up_stocks(3695)、keyword_analysis(10)、users.settings(3)

## 6. 日常运维

| 事项 | 说明 |
|---|---|
| 自动筛选 | backend 内置调度，每天 19:00（RUN_HOUR=19），页面可开关 |
| 行情更新 | cron 周一至五 18:03 tdx-daily 增量；日志 `/opt/TDX_daily/logs/cron.log` |
| 同花顺会话 | backend 自动心跳保活 |
| 重启 | `cd /opt/stock-review && docker compose restart` |
| 备份 | `pg_dump -U stock_user stock_review` + `pg_dump -U stock_user quantdb`（quantdb 可从 vipdoc 重建，优先备份 stock_review） |

## 7. 域名访问与备案（2026-09-28 实测）

域名 `ladder.yunqueai.cloud` 已正确解析到 `124.221.228.215`，但外部访问被拦。排查结论：

| 现象 | 实测结果 | 说明 |
|---|---|---|
| 外部 `curl http://ladder.yunqueai.cloud/` | `HTTP/1.1 302 OK` → `https://dnspod.qcloud.com/static/webblock.html?d=ladder.yunqueai.cloud` | 腾讯云**未接入备案**拦截 |
| 外部 `curl http://124.221.228.215/` | 200（`/api/health` → `{"status":"ok"}`） | 应用本身完全正常 |
| 服务器本机 `curl -H "Host: ladder.yunqueai.cloud" http://127.0.0.1/` | 200 | 拦截在**腾讯云网络侧**，nginx/应用无感知 |
| 域名 + 非 80 端口（7200） | 同样 302 | 拦截按 Host 做，不限于 80 |
| `-H "Host: totally-random-test-12345.com"` 直连该 IP | 200 | 腾讯云按“已知域名清单”拦，不是见未备案 Host 就拦 |
| 根域名 `yunqueai.cloud` | 解析到 `60.188.49.208`（CHINANET-ZJ-TZ 浙江电信台州），301 → HTTPS，正常服务 | 域名本身大概率已备案，但**接入商不是腾讯云** |

**结论（关键认知）**：ICP 备案不登记 IP，备案三要素是 **域名 + 主体 + 接入商**。所以不是“备案时漏了 IP”，
而是**该域名在腾讯云没有接入备案**（接入商不是腾讯云这台 CVM）。备案以根域名 `yunqueai.cloud` 为单位，
子域 `ladder.*` 不需要单独备案——在腾讯云为根域名做一次「新增接入」即可覆盖全部子域。

**修复路径**：
1. 腾讯云备案控制台 → 新增接入（用已有备案号复用主体信息）→ 绑定该 CVM 实例 → 提交管局审核（各省 1~20 工作日）
2. 生效前用 IP 访问 `http://124.221.228.215/`（已验证正常），或把服务放到接入商已备案的机房/境外机
3. 注意：`.cloud` 后缀能否备案以腾讯云备案控制台校验为准（本次外网备案查询接口均不可用，未取得官方结论）

## 8. 常见问题

| 现象 | 原因/解决 |
|---|---|
| DB 无表（"Did not find any relations"） | schema.sql 含 `CREATE DATABASE` 与 POSTGRES_DB 冲突 → 已从仓库移除；重建卷重试 |
| backend 连库报 no password / auth failed | .env 缺 `DB_PASSWORD` 或与 compose 硬编码不一致 → 统一为 `stock2024` |
| AI 分析 "Invalid URL" | .env 缺 `DEEPSEEK_API_URL` → compose 已加默认值 |
| AI 分析 402 / string indices | 网关账户余额不足 → 充值或换 key |
| **AI 分析接口返回 200 但内容是"分析失败"** | 推理模型(`deepseek-v4.x`)先输出 `reasoning_content` 吃掉预算，正文被截断/为空 → 后端日志 `API返回内容: `（空）+ `无法从返回内容中提取JSON` / `返回格式错误`。**根治办法是关思考**（见下一行），仅调大预算是治标 |
| **AI 关键词归并一直 500「AI 返回格式解析失败」** | 三天关键词 prompt 极长，推理模型会把预算全烧在思考上：实测 4096 预算 → `content=0`；提到 16000 → 仍 `content=0`、耗时 149s。已统一在 `app/core/llm_params.py` 发 `enable_thinking=false`（网关实测支持），同一 prompt 降到 2~4s、推理 0 token，正常返回 JSON |
| **思考开关 / 超时** | `DEEPSEEK_DISABLE_THINKING`（默认 `true`，关思考）、`DEEPSEEK_TIMEOUT`（默认 120s，原代码写死 60s 会让 40s+ 的个股分析直接超时）。需要推理质量时设为 `false` **并同步大幅调高 `DEEPSEEK_MAX_TOKENS_*`**，否则空正文老毛病复现 |
| **AI 分析变慢（关思考前个股分析约 35~41s）** | 关思考后为秒级。前端对 AI 接口本就单独放宽超时（`/stock/analyze` 120s、批量 120s，默认 30s 不适用于这些调用），新增 AI 调用记得一并放宽 |
| **改了 .env 但容器内环境变量没变** | compose 的 `environment:` 里写死了值会**覆盖** `env_file` → 改成 `${VAR:-默认值}` 形式（本次已修 4 个 DEEPSEEK_* 项） |
| **改了 `frontend/nginx.conf` 容器里没生效** | 该文件是单文件 bind mount，`sed -i` 会换 inode，容器仍读旧文件 → `docker restart stock-review-frontend-1` 重新挂载 |
| 域名打不开，curl 302 到 dnspod webblock | 域名在腾讯云**无接入备案** → 见第 7 节；备案前用 IP 访问 |
| 量化筛选 503 "TDX 行情库未配置" | .env 缺 `TDX_DATABASE_URL` 或 quantdb 未建 |
| embedding 模型警告刷日志 | 无 embed-cache；仅影响涨停天梯向量匹配，其余功能正常 |
