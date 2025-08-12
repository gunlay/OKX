# 本地开发环境设置指南

## 问题解决

✅ **问题已解决**：通过代理转发方案，现在可以在本地环境下正常开发和调试，无需将本地IP添加到OKX白名单。

## 解决方案概述

系统会自动检测运行环境：
- **本地环境**：使用 `OKXProxyClient`，通过AWS服务器代理转发OKX API请求
- **生产环境**：使用 `OKXClient`，直连OKX API

## 快速开始

### 1. 启动本地开发服务器

```bash
cd backend
python3 start_local.py
```

这个脚本会：
- 自动设置环境变量 `ENVIRONMENT=local`
- 配置代理服务器地址
- 启动FastAPI开发服务器（支持热重载）

### 2. 手动启动（可选）

如果你想手动控制环境变量：

```bash
cd backend
export ENVIRONMENT=local
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## 环境检测逻辑

系统按以下优先级检测环境：

1. **环境变量优先**
   - `ENVIRONMENT=local` → 本地环境
   - `ENVIRONMENT=production` → 生产环境

2. **自动检测**（当环境变量未设置时）
   - 检查主机名是否包含 "local"
   - 检查IP是否为内网地址（192.168.x.x, 10.x.x.x, 172.x.x.x, 127.0.0.1）
   - 检查是否为AWS服务器IP（13.158.74.102）
   - 默认认为是本地环境（安全选择）

## 工作原理

```
本地开发流程：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   本地前端      │───▶│   本地后端      │───▶│  AWS服务器代理  │
│  (Vue.js)      │    │ (FastAPI)      │    │   (FastAPI)    │
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
```

## 测试验证

### 1. 测试环境检测
```bash
cd backend
python3 test_environment.py
```

### 2. 测试API连接
启动服务后，在浏览器中访问：
```
http://localhost:8000/api/debug/status
```

### 3. 测试前端连接
```bash
cd frontend
npm run dev
```

## 文件说明

### 新增文件
- `backend/proxy_api.py` - 代理客户端实现
- `backend/start_local.py` - 本地开发启动脚本
- `backend/test_environment.py` - 环境检测测试脚本
- `backend/.env.example` - 环境变量示例
- `backend/PROXY_SETUP.md` - 详细技术文档

### 修改文件
- `backend/main.py` - 添加环境检测和代理接口

## 优势

✅ **无需修改OKX白名单**：本地IP不需要添加到OKX白名单
✅ **自动环境切换**：本地和生产环境自动适配
✅ **开发体验一致**：API调用方式完全相同
✅ **部署无影响**：生产环境无需任何修改
✅ **安全可靠**：代理请求通过HTTPS加密传输

## 注意事项

1. **网络延迟**：代理模式会增加一些网络延迟，但不影响开发调试
2. **服务器依赖**：需要确保AWS服务器正常运行
3. **API密钥安全**：代理请求中包含API密钥，确保使用HTTPS

## 故障排除

### 问题1：代理连接失败
```
解决方案：
1. 检查AWS服务器状态：http://13.158.74.102:8000/api/debug/status
2. 确认网络连接正常
3. 检查防火墙设置
```

### 问题2：环境检测错误
```
解决方案：
1. 手动设置环境变量：export ENVIRONMENT=local
2. 使用启动脚本：python3 start_local.py
3. 检查test_environment.py的输出
```

### 问题3：API调用失败
```
解决方案：
1. 确认OKX API密钥配置正确
2. 测试AWS服务器的OKX连接
3. 检查后端日志输出
```

## 开发工作流

1. **启动后端**：`python3 start_local.py`
2. **启动前端**：`npm run dev`
3. **开发调试**：正常使用，API会自动通过代理转发
4. **测试功能**：所有功能与生产环境一致
5. **提交代码**：无需特殊处理，代码可直接部署

现在你可以愉快地在本地环境下开发和调试了！🎉