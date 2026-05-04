#!/bin/bash
set -e

SERVER_IP="218.244.140.186"
SERVER_USER="root"
PROJECT_DIR="/opt/stock-review"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=========================================="
echo "涨停梯队分析系统 - Docker容器化部署"
echo "目标服务器: ${SERVER_IP}"
echo "=========================================="

echo ""
echo "[1/5] 检查SSH连接..."
ssh -o ConnectTimeout=5 ${SERVER_USER}@${SERVER_IP} "echo 'SSH连接成功'"

echo ""
echo "[2/5] 在服务器上安装Docker..."
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
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

echo ""
echo "[3/5] 同步项目文件到服务器..."
ssh ${SERVER_USER}@${SERVER_IP} "mkdir -p ${PROJECT_DIR}"
rsync -avz --exclude='node_modules' --exclude='*.pyc' --exclude='__pycache__' \
    --exclude='.git' --exclude='*.log' --exclude='venv' --exclude='.env' \
    --exclude='dist' \
    ${LOCAL_DIR}/ ${SERVER_USER}@${SERVER_IP}:${PROJECT_DIR}/

echo ""
echo "[4/5] 构建并启动Docker容器..."
ssh ${SERVER_USER}@${SERVER_IP} << ENDSSH
cd ${PROJECT_DIR}

echo "构建Docker镜像..."
docker compose build

echo "启动容器..."
docker compose down
docker compose up -d

echo "等待服务启动..."
sleep 10

echo "检查容器状态..."
docker compose ps
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
echo "=========================================="
