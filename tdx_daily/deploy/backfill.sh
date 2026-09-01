#!/bin/bash
# TDX_daily 首次历史灌库：逐日下载官网日线 zip（节假日失败自动跳过），
# 再导入 + 全量 basic/因子 + 复权视图 + 申万行业视图。
# 用法: bash backfill.sh 2025-09-01 2026-08-29
set -u
START=${1:-2025-09-01}
END=${2:-2026-08-29}
MERGE_DAY=${3:-2026-08-28}  # 须为真实交易日：最后用它触发一次全量合并
cd /opt/TDX_daily

echo "=== [1/4] 下载日线 $START ~ $END ==="
docker run --rm --network host --env-file /opt/TDX_daily/.env \
  -v /opt/TDX_daily/cache:/app/.cache \
  tdx-daily bash -c "
python - <<'EOF' > /tmp/dates.txt
import datetime
d = datetime.date.fromisoformat('$START')
end = datetime.date.fromisoformat('$END')
while d <= end:
    if d.weekday() < 5:
        print(d.isoformat())
    d += datetime.timedelta(days=1)
EOF
while read d; do
  # --skip-datatool 只下载解压不合并，避免 merge 全量历史导致 O(n²)；最后统一合并一次
  python download_g4day_daily.py --today \"\$d\" --skip-datatool > /tmp/dl.log 2>&1 && echo \"OK \$d\" || { echo \"SKIP \$d\"; tail -2 /tmp/dl.log; }
done < /tmp/dates.txt
# 最后再跑一个交易日（不带 --skip-datatool），一次性合并 refmhq 内全部历史到 vipdoc
python download_g4day_daily.py --today \"$MERGE_DAY\"
"

echo "=== [2/4] 导入日线 + GBBQ + basic + 因子 + 复权视图 ==="
docker run --rm --network host --env-file /opt/TDX_daily/.env \
  -v /opt/TDX_daily/cache:/app/.cache \
  tdx-daily python -u run_daily.py \
    --lday-path /app/.cache/web_daily/vipdoc \
    --min-date "$START" --full-basic --full-factor

echo "=== [3/4] 申万行业聚合视图 ==="
docker run --rm --network host --env-file /opt/TDX_daily/.env \
  tdx-daily python create_sw_views_standalone.py

echo "=== [4/4] 数据核对 ==="
docker exec stock-review-db-1 psql -U stock_user -d quantdb -c \
  "SELECT COUNT(*) AS rows, MIN(date) AS min_date, MAX(date) AS max_date, COUNT(DISTINCT symbol) AS symbols FROM tdx.raw_stocks_daily;"
echo "=== 灌库完成 ==="
