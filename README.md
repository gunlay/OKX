# OKX 定投服务系统

一个基于 OKX API 的自动化定投（DCA - Dollar Cost Averaging）服务系统，支持多币种、多频率的定投策略管理。

## 项目概述

本系统提供了一个完整的定投解决方案，包括：
- 🏠 **资产概览**：实时查看总资产、投入和收益
- 📈 **行情中心**：实时查看配置币种的价格和涨跌幅
- 📊 **交易记录**：详细的交易历史和筛选功能
- 📋 **任务中心**：灵活的定投计划管理
- ⚙️ **配置中心**：API密钥和币种配置

## 快速开始

### 本地开发环境

```bash
# 后端启动
cd backend
python3 start_local.py  # 自动设置代理模式

# 前端启动
cd frontend
npm run dev
```

### 生产环境部署

```bash
# 后端启动
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端构建
cd frontend
npm run build
```

## 技术架构

### 后端技术栈
- **框架**: FastAPI (Python)
- **数据库**: SQLite + SQLAlchemy ORM
- **定时任务**: APScheduler
- **API集成**: OKX REST API v5
- **安全**: Cryptography (API密钥加密存储)
- **日志**: Python logging

### 前端技术栈
- **框架**: Vue.js 3
- **构建工具**: Vite
- **HTTP客户端**: Axios
- **图表库**: ECharts
- **路由**: Vue Router 4
- **样式**: 原生CSS (移动端自适应)

### 项目结构
```
OKX/
├── backend/                 # 后端服务
│   ├── main.py             # FastAPI 主应用
│   ├── models.py           # 数据库模型
│   ├── okx_api.py          # OKX API 客户端
│   ├── proxy_api.py        # OKX 代理客户端
│   ├── start_local.py      # 本地开发启动脚本
│   └── dca.db              # SQLite 数据库
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   │   ├── Home.vue    # 首页
│   │   │   ├── Transactions.vue # 交易记录
│   │   │   ├── Tasks.vue   # 任务中心
│   │   │   └── Settings.vue # 配置中心
│   │   ├── components/     # 通用组件
│   │   │   └── AssetTrend.vue # 资产趋势图表
│   │   ├── api.js          # API 接口封装
│   │   ├── App.vue         # 根组件
│   │   └── main.js         # 入口文件
│   ├── package.json        # 依赖配置
│   └── vite.config.js      # 构建配置
├── needs/                  # 需求文档和设计图
├── ARCHITECTURE_GUIDE.md   # 架构设计与开发指南
└── README.md              # 项目文档
```

## 核心功能

### 1. 首页 - 资产概览
- **OKX账户余额**: 实时显示账户可用USDT余额
- **总资产**: 所有持仓币种的当前市值总和
- **总投入**: 所有成功交易的投入金额统计
- **总收益**: 总资产减去总投入，显示绝对收益和收益率
- **年化收益率**: 基于策略运行时间计算的年化收益
- **资产分布**: 各币种持仓占比的饼图展示
- **策略信息**: 策略开始时间、执行次数等
- **定投策略资产趋势**: 动态图表展示资产变化趋势

### 2. 交易记录
- **筛选功能**: 按币种、方向、日期范围筛选
- **详细信息**: 交易ID、币种、金额、价格、数量、状态、时间
- **实时数据**: 从OKX API获取真实成交数据
- **状态追踪**: 成功/失败状态，详细的错误信息

### 3. 任务中心
- **灵活调度**: 支持每日、每周、每月定投
- **多币种支持**: 支持所有OKX现货交易对
- **双向交易**: 支持买入和卖出策略
- **状态管理**: 启用/禁用任务，实时状态监控
- **手动执行**: 支持手动触发任务执行

### 4. 行情中心
- **实时价格**: 显示配置币种的当前价格
- **24小时数据**: 24小时最高价、最低价、涨跌幅
- **当日数据**: 基于北京时间0点的当日涨跌幅
- **价格对比**: 当前价格与24小时最高/最低价的对比
- **红涨绿跌**: 符合中国用户习惯的颜色显示
- **响应式布局**: 3行2列网格布局，适配移动端

### 5. 配置中心
- **API配置**: OKX API Key、Secret Key、Passphrase
- **安全存储**: API密钥采用Fernet加密存储
- **连接测试**: 实时测试API连接状态
- **币种管理**: 选择可交易的币种列表
- **热门币种**: 自动获取OKX交易量排名前列的币种

## API 接口

### 定投计划管理
- `GET /api/dca-plan` - 获取所有计划
- `POST /api/dca-plan` - 创建新计划
- `PUT /api/dca-plan/{id}` - 更新计划
- `DELETE /api/dca-plan/{id}` - 删除计划
- `PUT /api/dca-plan/{id}/status` - 更新计划状态
- `POST /api/dca-plan/{id}/execute` - 手动执行计划

### 资产数据
- `GET /api/assets/overview` - 获取资产概览
- `GET /api/assets/history` - 获取资产历史数据

### 交易记录
- `GET /api/transactions` - 获取交易记录

### 配置管理
- `POST /api/config/api` - 保存API配置
- `GET /api/config/api` - 获取API配置
- `POST /api/config/coins` - 保存币种配置
- `GET /api/config/coins` - 获取币种配置
- `GET /api/config/popular-coins` - 获取热门币种
- `POST /api/config/test` - 测试API连接

### 行情数据
- `GET /api/market/tickers` - 获取配置币种的实时行情数据

### 账户信息
- `GET /api/account/usdt-balance` - 获取OKX账户USDT余额

### 调试接口
- `GET /api/debug/status` - 获取系统状态信息

## 部署信息

### 服务器环境
- **服务器**: AWS EC2
- **公网IP**: 13.158.74.102
- **后端端口**: 8000
- **前端**: 静态文件部署

### 环境要求
- Python 3.8+
- Node.js 16+
- SQLite 3

### 安装依赖

#### 后端依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 前端依赖
```bash
cd frontend
npm install
```

## 更新日志

### v1.2.0 (2025-08-26)
- ✅ 新增行情中心功能，实时显示配置币种价格和涨跌幅
- ✅ 支持8个行情数据字段：当前价、24h最高/最低、24h涨跌幅、当日涨跌幅、距24h最高/最低价对比
- ✅ 采用红涨绿跌颜色方案，符合中国用户习惯
- ✅ 实现3行2列响应式网格布局，适配移动端
- ✅ 集成OKX API市场数据接口
- ✅ 优化环境检测和代理架构兼容性

### v1.1.0 (2025-08-09)
- ✅ 新增OKX账户USDT余额实时显示
- ✅ 优化首页按钮布局（刷新数据和退出按钮并排显示）
- ✅ 改进移动端按钮布局，保持左右排列
- ✅ 添加独立的USDT余额刷新功能
- ✅ 完善前端API调用和错误处理
- ✅ 增强调试日志和错误提示

### v1.0.0 (2025-08-09)
- ✅ 完成基础定投功能
- ✅ 支持多频率定投调度
- ✅ 实现资产概览和历史记录
- ✅ 完成移动端自适应界面
- ✅ 集成OKX API v5
- ✅ 实现API密钥加密存储

## 联系信息

如有问题或建议，请通过以下方式联系：
- 项目地址: `/Users/gunlay/Documents/Cursor/OKX`
- 服务器: http://13.158.74.102:8000

---

**免责声明**: 本系统仅供学习和研究使用，投资有风险，请谨慎使用。