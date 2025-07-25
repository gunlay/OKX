# OKX 定投服务后端

## 依赖安装

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## 主要接口

- POST /api/dca-plan 新建定投计划
- GET /api/dca-plan 获取定投计划列表
- PUT /api/dca-plan/{plan_id} 修改定投计划
- DELETE /api/dca-plan/{plan_id} 删除定投计划

## 说明
- 数据库存储在 `backend/dca.db`，为 SQLite 文件
- APScheduler 用于后续定时任务调度
- 后续可扩展 OKX API 对接、日志、API Key 管理等 