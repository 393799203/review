FROM python:3.11-slim

# 国内服务器拉 PyPI 走清华镜像；构建失败可去掉 -i 参数用官方源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 日常增量更新（容器由宿主机 cron 以 docker run --rm 方式触发）：
#   docker run --rm --network host --env-file /opt/TDX_daily/.env tdx-daily
# 灌历史数据：
#   docker run --rm --network host --env-file /opt/TDX_daily/.env tdx-daily \
#     python run_daily.py --download-daily --recent-days 370 --full-basic --full-factor
CMD ["python", "-u", "run_daily.py", "--download-daily"]
