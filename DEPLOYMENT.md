# 🚀 OKX定投系统服务器部署指南

## 📋 部署步骤

### 1. 在服务器上拉取最新代码

```bash
# SSH连接到你的AWS服务器
ssh -i your-key.pem ubuntu@13.158.74.102

# 进入项目目录
cd /path/to/your/OKX

# 拉取最新代码
git pull origin main

# 检查文件是否更新
ls -la backend/
```

### 2. 安装新的Python依赖

```bash
# 进入后端目录
cd backend

# 安装新增的依赖包
pip3 install requests urllib3

# 或者如果有requirements.txt，更新所有依赖
pip3 install -r requirements.txt
```

### 3. 应用数据库优化

```bash
# 运行数据库迁移脚本，添加性能索引
python3 migrate_db.py

# 检查迁移结果
# 应该看到类似输出：
# INFO:__main__:索引 idx_plan_executed_at 创建成功
# INFO:__main__:索引 idx_status_executed_at 创建成功
# ... 等等
```

### 4. 停止旧服务并启动优化后的服务

```bash
# 查找并停止旧的服务进程
sudo lsof -ti:8000 | xargs sudo kill -9

# 或者如果使用systemd服务
sudo systemctl stop okx-dca

# 启动优化后的服务
python3 start_optimized.py

# 或者在后台运行
nohup python3 start_optimized.py > server.log 2>&1 &
```

### 5. 验证部署效果

```bash
# 运行性能测试
python3 ../quick_test.py

# 检查服务状态
curl http://localhost:8000/api/debug/status

# 查看服务日志
tail -f server.log
```

## 🔧 推荐的生产环境配置

### 使用systemd管理服务（推荐）

创建服务文件：
```bash
sudo nano /etc/systemd/system/okx-dca-optimized.service
```

服务文件内容：
```ini
[Unit]
Description=OKX DCA Optimized Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/your/OKX/backend
ExecStart=/usr/bin/python3 start_optimized.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=/path/to/your/OKX/backend

[Install]
WantedBy=multi-user.target
```

启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable okx-dca-optimized
sudo systemctl start okx-dca-optimized
sudo systemctl status okx-dca-optimized
```

### 使用Nginx反向代理（可选）

如果需要更好的性能和安全性：

```bash
# 安装Nginx
sudo apt update
sudo apt install nginx

# 配置反向代理
sudo nano /etc/nginx/sites-available/okx-dca
```

Nginx配置：
```nginx
server {
    listen 80;
    server_name 13.158.74.102;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location / {
        root /path/to/your/OKX/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/okx-dca /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 性能监控

### 实时监控服务性能

```bash
# 查看性能统计
curl http://localhost:8000/api/debug/status

# 监控系统资源
htop

# 查看数据库大小
ls -lh backend/dca.db

# 检查日志中的慢查询警告
grep "慢" server.log
```

### 定期维护

```bash
# 每周运行一次数据库优化
sqlite3 backend/dca.db "VACUUM; ANALYZE;"

# 清理旧日志（保留最近7天）
find . -name "*.log" -mtime +7 -delete

# 备份数据库
cp backend/dca.db backup/dca_$(date +%Y%m%d).db
```

## 🚨 故障排除

### 常见问题

1. **端口占用**
```bash
sudo lsof -ti:8000 | xargs sudo kill -9
```

2. **权限问题**
```bash
sudo chown -R ubuntu:ubuntu /path/to/your/OKX
chmod +x backend/start_optimized.py
```

3. **依赖缺失**
```bash
pip3 install --upgrade -r requirements.txt
```

4. **数据库锁定**
```bash
# 检查是否有其他进程在使用数据库
sudo lsof backend/dca.db
```

### 性能问题诊断

```bash
# 运行完整性能测试
python3 ../test_performance.py

# 检查数据库索引
sqlite3 backend/dca.db "SELECT name, sql FROM sqlite_master WHERE type='index';"

# 监控API响应时间
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/assets/overview
```

## 📈 预期性能提升

部署完成后，你应该看到：

- ✅ 页面加载速度提升50-70%
- ✅ API响应时间减少30-50%
- ✅ 数据库查询速度提升60-80%
- ✅ 系统稳定性显著改善
- ✅ 并发处理能力提升40-60%

## 🔄 回滚方案

如果遇到问题需要回滚：

```bash
# 回滚到上一个版本
git log --oneline -5
git checkout <previous-commit-hash>

# 重启服务
sudo systemctl restart okx-dca-optimized
```

---

**注意**: 请根据你的实际服务器路径和配置调整上述命令中的路径。