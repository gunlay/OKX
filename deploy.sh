#!/bin/bash

# 🚀 OKX定投系统快速部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始部署OKX定投系统优化版本..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在正确的目录
if [ ! -f "backend/main.py" ]; then
    print_error "请在OKX项目根目录下运行此脚本"
    exit 1
fi

print_status "检查Python环境..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 未安装"
    exit 1
fi

print_status "安装/更新Python依赖..."
cd backend
pip3 install requests urllib3 --quiet

print_status "检查数据库文件..."
if [ ! -f "dca.db" ]; then
    print_warning "数据库文件不存在，将创建新的数据库"
    python3 -c "
from main import Base, engine
Base.metadata.create_all(bind=engine)
print('数据库创建完成')
"
fi

print_status "应用数据库优化（添加索引）..."
python3 migrate_db.py

print_status "停止旧服务..."
# 查找并停止占用8000端口的进程
if lsof -ti:8000 >/dev/null 2>&1; then
    print_warning "发现端口8000被占用，正在停止旧服务..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

print_status "启动优化后的服务..."
nohup python3 start_optimized.py > server.log 2>&1 &
SERVER_PID=$!

print_status "等待服务启动..."
sleep 5

# 检查服务是否启动成功
if ps -p $SERVER_PID > /dev/null; then
    print_status "服务启动成功，PID: $SERVER_PID"
else
    print_error "服务启动失败，请检查日志："
    tail -20 server.log
    exit 1
fi

print_status "运行性能测试..."
cd ..
if python3 quick_test.py; then
    echo ""
    echo "🎉 部署成功！"
    echo "📊 性能测试通过"
    echo "🌐 服务地址: http://$(hostname -I | awk '{print $1}'):8000"
    echo "📋 服务PID: $SERVER_PID"
    echo "📝 日志文件: backend/server.log"
    echo ""
    echo "💡 常用命令："
    echo "  查看日志: tail -f backend/server.log"
    echo "  停止服务: kill $SERVER_PID"
    echo "  重启服务: cd backend && python3 start_optimized.py"
else
    print_warning "性能测试未完全通过，但服务已启动"
    echo "请检查API配置和网络连接"
fi

print_status "部署完成！"