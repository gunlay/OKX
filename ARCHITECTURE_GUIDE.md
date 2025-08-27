# OKX定投系统架构设计与开发指南

## 系统架构概述

本系统采用**代理转发架构**，解决OKX API的IP白名单限制问题，实现本地开发与线上部署的无缝切换。

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        整体架构流程                              │
└─────────────────────────────────────────────────────────────────┘

本地开发环境：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   本地前端      │───▶│   本地后端      │───▶│  AWS服务器代理  │
│  (Vue.js)      │    │ (FastAPI)      │    │   (FastAPI)    │
│ localhost:5173 │    │ localhost:8000 │    │13.158.74.102   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ OKXProxyClient │    │   OKXClient    │
                    │   (代理模式)    │    │   (直连模式)    │
                    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                           ┌─────────────────┐
                                           │    OKX API     │
                                           │  (需要IP白名单)  │
                                           └─────────────────┘

生产环境：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端页面      │───▶│  AWS后端服务    │───▶│    OKX API     │
│13.158.74.102   │    │13.158.74.102   │    │  (直连访问)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心组件说明

### 1. 线上服务器（AWS - 13.158.74.102:8000）

**职责**：
- 运行完整的FastAPI后端服务
- 存储真实的OKX API密钥配置
- 直连OKX API（IP已加入白名单）
- 为本地开发提供代理转发服务

**关键特性**：
- ✅ 配置了完整的OKX API密钥（api_key, secret_key, passphrase）
- ✅ IP地址已加入OKX白名单，可直接访问OKX API
- ✅ 数据库存储所有业务数据（DCA计划、交易记录、配置等）
- ✅ 提供代理接口 `/api/proxy/okx` 供本地开发使用

### 2. 本地开发环境

**职责**：
- 前端开发和调试
- 后端逻辑开发和测试
- 通过代理访问OKX API

**启动方式**：
```bash
# 后端
cd backend
python3 start_local.py

# 前端
cd frontend
npm run dev
```

**工作原理**：
- 环境变量 `ENVIRONMENT=local` 触发代理模式
- 使用 `OKXProxyClient` 替代 `OKXClient`
- 所有OKX API请求转发到线上服务器

## 本地开发环境设置

### 快速开始

#### 1. 启动本地开发服务器

```bash
cd backend
python3 start_local.py
```

这个脚本会：
- 自动设置环境变量 `ENVIRONMENT=local`
- 配置代理服务器地址
- 启动FastAPI开发服务器（支持热重载）

#### 2. 手动启动（可选）

如果你想手动控制环境变量：

```bash
# 设置本地开发环境
export ENVIRONMENT=local
export PROXY_SERVER_URL=http://13.158.74.102:8000

# 启动后端
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端
cd frontend
npm run dev
```

### 环境检测机制

系统通过 `is_local_environment()` 函数自动检测运行环境：

```python
def is_local_environment():
    """检测是否为本地开发环境"""
    return os.getenv('ENVIRONMENT') == 'local'
```

**环境切换逻辑**：
- `ENVIRONMENT=local` → 使用代理模式（OKXProxyClient）
- `ENVIRONMENT!=local` → 使用直连模式（OKXClient）

### 代理客户端实现

```python
class OKXProxyClient:
    def __init__(self, api_key, secret_key, passphrase):
        self.proxy_url = "http://13.158.74.102:8000/api/proxy/okx"
    
    def get_account_balance(self):
        # 通过代理服务器获取账户余额
        response = requests.post(f"{self.proxy_url}/account/balance")
        return response.json()
    
    def place_order(self, symbol, side, amount):
        # 通过代理服务器下单
        data = {"symbol": symbol, "side": side, "amount": amount}
        response = requests.post(f"{self.proxy_url}/trade/order", json=data)
        return response.json()
```

## 核心功能架构

### 1. 定投策略管理
- **计划创建**: 支持多币种、多频率的定投计划
- **自动执行**: 基于APScheduler的定时任务调度
- **状态管理**: 启用/禁用、暂停/恢复功能
- **风险控制**: 余额检查、价格保护机制

### 2. 交易执行引擎
- **订单管理**: 市价单自动执行
- **错误处理**: 完善的异常捕获和重试机制
- **日志记录**: 详细的交易日志和审计跟踪
- **状态同步**: 实时同步OKX交易状态

### 3. 资产数据管理
- **实时价格获取**: 通过OKX API获取最新价格
- **历史数据存储**: 资产变化历史记录
- **收益计算**: 实时计算收益率和年化收益
- **数据可视化**: ECharts图表展示资产趋势

### 4. 行情数据管理
- **实时行情获取**: 通过OKX API获取配置币种的实时价格数据
- **多维度数据展示**: 支持8个数据字段（当前价、24h最高/最低、涨跌幅对比等）
- **环境适配**: 自动检测本地/生产环境，使用相应的API客户端
- **数据处理**: 自动计算各种涨跌幅和价格对比指标
- **格式兼容**: 支持BTC和BTC-USDT两种币种格式的自动转换
- **服务架构**: MarketService负责行情数据业务逻辑，支持依赖注入和环境适配
- **字段完整性**: 确保前后端字段名匹配，包含格式化显示字段

### 5. 用户体验
- **移动端自适应设计**: 响应式布局，支持手机和平板访问
- **实时数据刷新**: 支持手动刷新资产数据、USDT余额和行情数据
- **直观的图表展示**: ECharts图表展示资产趋势和分布
- **友好的错误提示**: 详细的错误信息和加载状态提示
- **独立余额显示**: OKX账户USDT余额独立显示，不计入定投策略资产
- **便捷操作**: 刷新数据和退出按钮并排显示，操作更便捷
- **中式颜色方案**: 行情数据采用红涨绿跌颜色显示，符合中国用户习惯
- **网格布局**: 行情中心采用3行2列响应式网格布局，信息展示更清晰

## 故障排除指南

### 常见问题

1. **API配置丢失**
   ```bash
   # 症状：配置中心显示"未找到API配置"
   # 原因：数据库被清空或API配置表被删除
   # 解决：回滚到最近的稳定版本
   git reset --hard <stable_commit>
   git push --force origin main
   ```

2. **代理连接失败**
   ```bash
   # 症状：本地开发时API请求失败
   # 检查：线上服务器状态
   curl http://13.158.74.102:8000/health
   
   # 检查：代理端点
   curl http://13.158.74.102:8000/api/proxy/okx
   ```

3. **环境检测错误**
   ```bash
   # 手动设置环境变量
   export ENVIRONMENT=local
   python3 start_local.py
   ```

4. **MarketService初始化错误**
   ```bash
   # 症状：NameError: name 'market_service' is not defined
   # 原因：MarketService未正确初始化或缺少依赖参数
   # 检查：确保market_service在create_okx_client函数定义之后初始化
   # 解决：
   market_service = MarketService(SessionLocal, config_service, create_okx_client)
   ```

5. **行情数据字段缺失**
   ```bash
   # 症状：前端行情页面某些字段显示为空
   # 原因：前后端字段名不匹配
   # 检查：确保后端返回包含以下字段：
   # - changePercent24h (24h涨跌幅格式化)
   # - changePercentDaily (当日涨跌幅格式化)
   # - changeFromHighPercent (距24h最高格式化)
   # - changeFromLowPercent (距24h最低格式化)
   ```

### 紧急恢复流程

1. **立即回滚**
   ```bash
   git log --oneline -10  # 查看最近提交
   git reset --hard <last_stable_commit>
   git push --force origin main
   ```

2. **数据库恢复**
   ```bash
   # 如果有备份文件
   cp backup/dca_trading.db ./dca_trading.db
   
   # 重启服务
   sudo systemctl restart okx-dca
   ```

3. **服务重启**
   ```bash
   # AWS服务器上
   sudo systemctl status okx-dca
   sudo systemctl restart okx-dca
   sudo systemctl enable okx-dca
   ```

## 开发规范

### 🚫 禁止的操作

1. **线上环境直接修改**
   - 不得直接在AWS服务器上修改代码
   - 不得直接修改线上数据库
   - 不得在生产环境直接测试未验证的代码

### ✅ 允许的操作

1. **前端开发**
   - 可以自由修改Vue.js组件
   - 可以添加新的页面和功能
   - 可以优化UI/UX体验

2. **后端功能扩展**
   - 可以添加新的API端点
   - 可以优化现有业务逻辑
   - 可以添加新的数据模型（保持向后兼容）

3. **代码优化**
   - 可以重构代码提高可读性
   - 可以优化性能和错误处理
   - 可以添加日志和监控

### ⚠️ 需要谨慎的操作

1. **数据库相关修改**
   - 修改前必须备份数据
   - 确保向后兼容性
   - 在本地充分测试

2. **API接口修改**
   - 保持接口向后兼容
   - 更新相关文档
   - 通知前端开发者

3. **依赖库更新**
   - 测试兼容性
   - 检查安全漏洞
   - 逐步升级

## 开发工作流

### 本地开发流程

1. **环境准备**
   ```bash
   git pull origin main
   cd backend
   python3 start_local.py  # 自动设置代理模式
   ```

2. **前端开发**
   ```bash
   cd frontend
   npm run dev
   ```

3. **功能测试**
   - 在本地环境充分测试新功能
   - 确保不影响现有功能
   - 验证代理模式正常工作

4. **代码提交**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   git push origin main
   ```

### 生产部署流程

1. **代码同步**
   ```bash
   # 在AWS服务器上
   cd /path/to/okx-dca
   git pull origin main
   ```

2. **依赖更新**
   ```bash
   # 如果有新依赖
   pip install -r requirements.txt
   npm install  # 如果前端有更新
   ```

3. **服务重启**
   ```bash
   sudo systemctl restart okx-dca
   sudo systemctl status okx-dca
   ```

4. **功能验证**
   - 访问线上服务验证功能正常
   - 检查日志确认无错误
   - 监控系统运行状态

## 技术栈说明

### 后端技术栈
- **FastAPI**: 现代化的Python Web框架
- **SQLite**: 轻量级数据库，适合单机部署
- **APScheduler**: Python任务调度库
- **OKX API v5**: 官方交易接口
- **Cryptography**: 数据加密库

### 前端技术栈
- **Vue.js 3**: 渐进式JavaScript框架
- **Vite**: 现代化构建工具
- **ECharts**: 数据可视化图表库
- **Axios**: HTTP客户端库

### 部署环境
- **AWS EC2**: 云服务器
- **Ubuntu**: 操作系统
- **Systemd**: 服务管理
- **Nginx**: 反向代理（可选）

## 安全考虑

### API密钥安全
- 使用Fernet对称加密存储API密钥
- 密钥仅在内存中解密使用
- 定期轮换加密密钥

### 网络安全
- OKX API白名单IP限制
- HTTPS加密传输
- 代理服务器访问控制

### 数据安全
- 定期备份数据库
- 敏感数据加密存储
- 访问日志记录

## 性能优化

### 数据库优化
- 合理的索引设计
- 定期清理历史数据
- 连接池管理

### API调用优化
- 请求频率控制
- 错误重试机制
- 响应缓存策略

### 前端优化
- 组件懒加载
- 图片压缩优化
- 代码分割打包

## 监控和日志

### 系统监控
- 服务运行状态监控
- API调用成功率监控
- 数据库性能监控

### 日志管理
- 结构化日志格式
- 日志级别分类
- 日志轮转和清理

### 告警机制
- 交易失败告警
- 系统异常告警
- 资源使用告警

## 扩展性考虑

### 水平扩展
- 数据库分离部署
- 负载均衡配置
- 微服务架构演进

### 功能扩展
- 插件化架构设计
- API版本管理
- 配置热更新

## 交易风险管理

### 风险控制机制
- 最大单笔交易金额限制
- 日交易次数限制
- 异常价格保护

### 交易监控
- 实时交易状态监控
- 异常交易检测
- 风险指标计算

### 应急处理
- 紧急停止机制
- 交易回滚流程
- 风险事件响应

## 合规性考虑

### 数据合规
- 用户数据保护
- 交易记录完整性
- 审计日志要求

### 交易合规
- 反洗钱(AML)要求
- 了解客户(KYC)流程
- 监管报告要求

## 技术债务管理

### 代码质量
- 代码审查流程
- 单元测试覆盖
- 技术债务跟踪

### 依赖管理
- 依赖版本锁定
- 安全漏洞扫描
- 定期依赖更新

## 业务逻辑说明

### 定投策略
- 支持固定金额和固定数量两种模式
- 支持多种执行频率（每日、每周、每月）
- 智能价格保护和风险控制

### 收益计算
- 基于实际成交价格计算收益
- 支持多币种收益汇总
- 年化收益率自动计算

### 交易执行
- 市价单和限价单的不同处理逻辑

### 系统限制
- 仅支持现货交易
- 基于USDT计价
- 需要足够的账户余额

### 安全建议
- 定期备份数据库
- 监控API密钥安全
- 关注交易异常情况

## API接口文档

### 行情数据接口

#### GET /api/market/tickers
获取配置币种的实时行情数据

**请求参数**: 无

**响应格式**:
```json
{
  "success": true,
  "data": [
    {
      "symbol": "BTC",
      "instId": "BTC-USDT", 
      "price": 43250.5,
      "high24h": 44000.0,
      "low24h": 42800.0,
      "change24h": 1.25,
      "changePercent24h": "+1.25%",
      "changeDaily": 0.85,
      "changePercentDaily": "+0.85%",
      "changeFromHigh": -1.70,
      "changeFromHighPercent": "-1.70%",
      "changeFromLow": 1.05,
      "changeFromLowPercent": "+1.05%"
    }
  ]
}
```

**数据字段说明**:
- `symbol`: 币种符号（如BTC）
- `instId`: OKX交易对标识（如BTC-USDT）
- `price`: 当前价格
- `high24h`: 24小时最高价
- `low24h`: 24小时最低价
- `change24h`: 24小时涨跌幅（%）
- `changeDaily`: 当日涨跌幅（基于北京时间0点，%）
- `changeFromHigh`: 当前价格距24h最高价的跌幅（%）
- `changeFromLow`: 当前价格距24h最低价的涨幅（%）

**环境适配**:
- 本地环境：通过代理服务器获取数据
- 生产环境：直接调用OKX API

## 对开发者的提醒

1. **理解架构再动手**
   - 修改代码前必须完全理解现有架构
   - 不确定时先询问或查看文档
   - 大规模修改前先在分支中测试

2. **保护线上环境**
   - 线上服务器是生产环境，必须保持稳定
   - 任何可能影响稳定性的修改都要谨慎
   - 出现问题立即回滚，不要尝试在线修复

3. **遵循开发流程**
   - 本地开发 → 测试验证 → 代码提交 → 生产部署
   - 不要跳过任何环节
   - 保持代码和文档同步更新

---

**文档版本**: v1.2  
**最后更新**: 2025-08-26  
**维护者**: 开发团队