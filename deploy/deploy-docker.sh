#!/bin/bash
set -e

SERVER_IP="192.168.110.115"
SERVER_USER="root"
PROJECT_DIR="/opt/stock-review"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SSH_KEY="~/.ssh/review_server"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no"

FRONTEND_ONLY=false

for arg in "$@"; do
    if [ "$arg" = "--frontend-only" ] || [ "$arg" = "-f" ]; then
        FRONTEND_ONLY=true
    fi
done

echo "=========================================="
echo "云雀AI - Docker容器化部署"
echo "目标服务器: ${SERVER_IP}"
if [ "$FRONTEND_ONLY" = true ]; then
    echo "部署模式: 仅前端"
fi
echo "=========================================="

echo ""
echo "[1/5] 检查SSH连接..."
ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} "echo 'SSH连接成功'"

if [ "$FRONTEND_ONLY" = false ]; then
    echo ""
    echo "[2/5] 在服务器上安装Docker..."
    ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker安装完成"
else
    echo "Docker已安装"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "安装Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose安装完成"
else
    echo "Docker Compose已安装"
fi
ENDSSH
fi

echo ""
echo "[3/5] 本地构建前端并同步项目文件到服务器..."
cd ${LOCAL_DIR}/frontend && npm run build && cd ${LOCAL_DIR}
ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} "mkdir -p ${PROJECT_DIR}/frontend"

if [ "$FRONTEND_ONLY" = true ]; then
    # 前端为本地构建产物(nginx 直接挂载 dist),只需同步 dist 和 nginx.conf
    rsync -avz --delete -e "ssh ${SSH_OPTS}" ${LOCAL_DIR}/frontend/dist ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/frontend/
    rsync -avz -e "ssh ${SSH_OPTS}" ${LOCAL_DIR}/frontend/nginx.conf ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/frontend/
    rsync -avz -e "ssh ${SSH_OPTS}" ${LOCAL_DIR}/docker-compose.yml ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/
else
    rsync -avz -e "ssh ${SSH_OPTS}" --exclude='node_modules' --exclude='*.pyc' --exclude='__pycache__' \
        --exclude='.git' --exclude='*.log' --exclude='venv' --exclude='.env' \
        ${LOCAL_DIR}/ ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/
fi

echo ""
echo "[4/5] 构建并启动Docker容器..."
ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_IP} << ENDSSH
set -e
cd ${PROJECT_DIR}

if [ "$FRONTEND_ONLY" = true ]; then
    # 前端无需在服务器构建，直接用最新 dist 重建容器
    echo "重建前端容器(本地构建产物)..."
    docker compose up -d --force-recreate frontend
else
    # 磁盘空间不足时先自动清理，避免构建因 ENOSPC 静默失败
    AVAIL_GB=\$(df --output=avail -BG / | tail -1 | tr -dc '0-9')
    if [ "\$AVAIL_GB" -lt 3 ]; then
        echo "磁盘可用空间不足(\${AVAIL_GB}G),自动清理 Docker 构建缓存和悬空镜像..."
        docker builder prune -af
        docker image prune -f
    fi

    echo "构建后端Docker镜像(前端为本地构建产物,无需服务器构建)..."
    docker compose build --no-cache backend
    echo "启动容器..."
    docker compose down
    docker compose up -d
fi

echo "等待服务启动..."
sleep 10

echo "检查容器状态..."
docker compose ps

# 关键容器必须处于运行状态，否则判定部署失败
if [ "$FRONTEND_ONLY" = true ]; then
    docker compose ps frontend --status running --format '{{.Name}}' | grep -q frontend || { echo "✗ 前端容器未正常运行,部署失败"; exit 1; }
else
    docker compose ps backend --status running --format '{{.Name}}' | grep -q backend || { echo "✗ 后端容器未正常运行,部署失败"; exit 1; }
    docker compose ps frontend --status running --format '{{.Name}}' | grep -q frontend || { echo "✗ 前端容器未正常运行,部署失败"; exit 1; }
fi

# 部署成功后清理构建缓存和悬空镜像，防止磁盘被 Docker 占满
docker builder prune -f > /dev/null 2>&1 || true
docker image prune -f > /dev/null 2>&1 || true
ENDSSH

echo ""
echo "[5/5] 验证部署..."
sleep 5
curl -s http://${SERVER_IP}/api/health | python3 -m json.tool || echo "服务启动中，请稍后访问..."

echo ""
echo "=========================================="
echo "部署完成！"
echo ""
echo "访问地址:"
echo "  前端页面: http://${SERVER_IP}"
echo "  后端API: http://${SERVER_IP}/api"
echo "  健康检查: http://${SERVER_IP}/api/health"
echo ""
echo "常用命令:"
echo "  查看日志: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${PROJECT_DIR} && docker compose logs -f'"
echo "  重启服务: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${PROJECT_DIR} && docker compose restart'"
echo "  停止服务: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${PROJECT_DIR} && docker compose down'"
echo ""
echo "仅部署前端: bash deploy-docker.sh --frontend-only"
echo "=========================================="
