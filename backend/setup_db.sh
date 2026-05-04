#!/bin/bash
# PostgreSQL安装和数据库创建脚本

echo "=================================="
echo "PostgreSQL 18 安装和配置"
echo "=================================="
echo ""

# 检查PostgreSQL是否已安装
if brew list postgresql@18 &> /dev/null; then
    echo "✅ PostgreSQL 18 已安装"
else
    echo "正在安装 PostgreSQL 18..."
    brew install postgresql@18
fi

# 等待安装完成
echo "等待安装完成..."
sleep 5

# 链接PostgreSQL
echo "链接 PostgreSQL..."
brew link postgresql@18 --force 2>/dev/null || true

# 启动PostgreSQL服务
echo "启动 PostgreSQL 服务..."
brew services start postgresql@18

# 等待服务启动
echo "等待服务启动..."
sleep 3

# 创建数据库
echo "创建数据库..."
createdb stock_review 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 数据库 stock_review 创建成功"
else
    echo "数据库可能已存在，继续..."
fi

# 验证数据库
echo ""
echo "验证数据库..."
psql -l | grep stock_review

echo ""
echo "=================================="
echo "PostgreSQL 配置完成！"
echo "=================================="
echo ""
echo "数据库信息:"
echo "  数据库名: stock_review"
echo "  主机: localhost"
echo "  端口: 5432"
echo "  用户: $(whoami)"
echo ""
echo "下一步:"
echo "  cd /Users/dingyuebo/projects/stock/review"
echo "  python3 -c 'from models import init_database; init_database()'"
echo "  python3 fetch_data.py --recent 5"
echo "  python3 app.py"
echo ""
