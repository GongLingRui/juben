# Middleware模块流程分析

## 功能概述

Middleware模块提供HTTP中间件功能，主要负责CORS跨域配置和请求预处理，确保前端可以正常访问后端API。

## 入口方法

```
middleware/cors_middleware.py:add_cors_middleware()
```

## 方法调用树

```
Middleware模块
├─ cors_middleware.py - CORS中间件
│  ├─ add_cors_middleware(app) - 添加CORS中间件
│  │  ├─ 配置allow_origins
│  │  ├─ 检查DEBUG环境变量
│  │  └─ 调用app.add_middleware()
│  └─ CORSMiddlewareConfig - CORS配置类
│     ├─ ALLOW_ORIGINS - 允许的源列表
│     ├─ ALLOW_CREDENTIALS - 允许携带凭证
│     ├─ ALLOW_METHODS - 允许的HTTP方法
│     ├─ ALLOW_HEADERS - 允许的请求头
│     └─ add_to_app(app) - 添加到应用
└─ auth_middleware.py - 认证中间件(如果存在)
```

## 详细业务流程

### 1. CORS中间件添加流程

```
1. 应用启动时调用add_cors_middleware(app)
   - 传入FastAPI应用实例

2. 配置允许的源列表
   默认配置:
   - http://localhost:5173 (Vite开发服务器)
   - http://localhost:3000 (备用端口)
   - http://127.0.0.1:5173
   - http://127.0.0.1:3000
   - https://your-domain.com (生产环境)

3. 检查DEBUG环境变量
   - 如果DEBUG=true, 允许所有源 (*)
   - 否则使用配置的源列表

4. 添加中间件到应用
   app.add_middleware(
       CORSMiddleware,
       allow_origins=allow_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
       expose_headers=["*"]
   )
```

### 2. CORS配置类流程

```
1. 定义CORSMiddlewareConfig类
   - ALLOW_ORIGINS: List[str] - 允许的源
   - ALLOW_CREDENTIALS: bool = True - 允许凭证
   - ALLOW_METHODS: List[str] = ["*"] - 允许所有方法
   - ALLOW_HEADERS: List[str] = ["*"] - 允许所有头
   - EXPOSE_HEADERS: List[str] = ["*"] - 暴露所有头

2. 提供add_to_app类方法
   - 检查DEBUG环境变量
   - 动态调整allow_origins
   - 添加中间件到应用
```

## 关键业务规则

### CORS配置规则
- **开发环境**: DEBUG=true时允许所有源 (*)
- **生产环境**: 仅允许配置的源列表
- **凭证支持**: allow_credentials=True支持携带Cookie
- **方法支持**: 允许所有HTTP方法
- **头支持**: 允许所有请求头

### 端口配置
- **5173**: Vite默认开发端口
- **3000**: 备用开发端口
- **生产域名**: 需要配置实际的生产域名

## 数据流转

### 请求处理流程
```
前端请求
  → CORS中间件验证
  → 检查Origin是否在allow_origins中
  → 添加CORS响应头:
    - Access-Control-Allow-Origin
    - Access-Control-Allow-Credentials
    - Access-Control-Allow-Methods
    - Access-Control-Allow-Headers
  → 传递给路由处理器
```

### 预检请求(OPTIONS)
```
OPTIONS请求
  → CORS中间件直接响应
  → 返回允许的方法和头
  → 不传递给路由处理器
```

## 扩展点/分支逻辑

### 环境分支
- **开发环境**: DEBUG=true, 允许所有源
- **生产环境**: DEBUG=false, 使用配置的源列表

### 源验证分支
- **允许的源**: 返回Access-Control-Allow-Origin: 具体源
- **不允许的源**: 拒绝请求,返回CORS错误

## 外部依赖

### FastAPI
- CORSMiddleware - FastAPI内置的CORS中间件

### 环境变量
- DEBUG - 开发模式标志

## 注意事项

### 安全考虑
1. **生产环境**: 不要在生产环境使用允许所有源 (*)
2. **凭证模式**: 配置具体源列表时才能使用allow_credentials=True
3. **域名配置**: 生产环境需要配置实际的生产域名

### 开发体验
1. **热重载**: Vite开发服务器端口5173
2. **调试**: DEBUG=true时允许所有源,方便调试

### 配置管理
1. **集中配置**: 使用CORSMiddlewareConfig统一管理配置
2. **环境适配**: 根据环境变量自动调整配置
