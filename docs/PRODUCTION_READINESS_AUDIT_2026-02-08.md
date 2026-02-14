# 剧本创作 Agent 平台 - 生产就绪审计报告

生成时间：2026-02-08

## 范围与方法
- 代码静态审阅（后端、前端、配置、部署与运行脚本）
- 重点关注：安全性、稳定性、可观测性、可维护性与可部署性
- 未运行测试与基准压测，仅基于当前代码与配置判断

## 结论摘要
当前系统功能面广，但生产级关键环节仍存在高风险缺口，主要集中在认证默认关闭、密钥泄露、鉴权与限流不足、SSE 反向代理配置不当、前端构建产物缺失、依赖不可复现、基础设施默认弱配置等方面。若要达到“生产级最优秀应用”，需要先完成安全与部署基线改造，再推进架构与性能优化。

---

## P0（必须立即处理）

1) 认证默认关闭导致全量接口裸奔
- 位置：main.py
- 问题：AUTH_ENABLED 默认 false，生产环境很容易被误部署为无鉴权模式
- 风险：所有 API 暴露、敏感数据泄露

2) 仓库内存在真实密钥/凭据
- 位置：.env
- 问题：出现真实 API Key / Service Role Key / OpenAI Key
- 风险：密钥泄露、账户被盗用、合规风险

3) 鉴权与用户数据使用内存存储
- 位置：apis/auth/api_routes_auth.py
- 问题：用户数据存储在内存，重启即丢；生产无法审计与回收
- 风险：不可扩展、不可追踪、权限体系形同虚设

4) Token 黑名单内存实现
- 位置：utils/jwt_auth.py
- 问题：黑名单基于内存 set，无法跨实例同步
- 风险：横向扩容失效、退出登录无效

5) SSE 反向代理缓冲导致流式中断
- 位置：nginx.conf、apis/core/api_routes.py
- 问题：Nginx 对 /api/ 启用 proxy_buffering，会破坏 SSE 实时性
- 风险：实时流式输出失效，用户体验严重下降

6) 前端生产构建产物缺失
- 位置：Dockerfile、main.py
- 问题：main.py 依赖 frontend/dist，但 Dockerfile 未构建前端
- 风险：生产部署没有 UI 或 UI 失效

7) 默认弱凭据与暴露端口
- 位置：docker-compose.yml
- 问题：MinIO 默认账号、Grafana 默认密码、Redis/Milvus 暴露端口
- 风险：被直接扫到即被接管或数据泄露

---

## P1（高优先级）

1) CORS 与安全头缺失
- 位置：middleware/cors_middleware.py、nginx.conf
- 问题：DEBUG 时 allow_origins 为 "*" 且 allow_credentials 为 true；Nginx 也为 API 放开 "*"
- 风险：凭据泄露、跨站访问

2) 限流未统一生效
- 位置：middleware/auth_middleware.py、utils/rate_limit_dependencies.py
- 问题：RateLimitMiddleware 没有在 main.py 使用；Nginx 限流只按 IP
- 风险：易被刷、成本飙升

3) 依赖版本不可复现
- 位置：requirements.txt、frontend/package.json
- 问题：大量使用 >= 或 ^，缺少 Python 锁文件
- 风险：部署不可重复、线上漂移

4) 日志与审计缺少轮转与集中化
- 位置：utils/logger_config.py
- 问题：文件日志无轮转，生产长期运行会填满磁盘
- 风险：磁盘耗尽导致服务不可用

5) 数据库与存储缺少迁移体系
- 位置：init_database.py、数据库相关 utils
- 问题：无 schema 版本管理与回滚策略
- 风险：线上升级不可控

6) 前端依赖产物在仓库中
- 位置：frontend/node_modules
- 问题：node_modules 被提交，增大仓库与构建混乱
- 风险：安全与维护成本提升

7) Auth 相关接口缺少防暴力攻击
- 位置：apis/auth/api_routes_auth.py
- 问题：无登录失败计数、无锁定策略、无验证码/限速
- 风险：账号可被暴力破解

---

## P2（中优先级）

1) SSE 缺少代理层优化配置
- 位置：nginx.conf
- 问题：未设置 X-Accel-Buffering: no，未显式禁用压缩
- 风险：流式响应卡顿

2) 环境配置未强制分层
- 位置：config/config.yaml、main.py
- 问题：没有 dev/staging/prod 严格分层配置
- 风险：配置混用导致事故

3) 多模块缓存与内存策略无统一规范
- 位置：utils/*
- 问题：多处 in-memory 缓存、无统一 TTL 与容量
- 风险：内存泄露或突发占用

4) CI/CD 流程缺失
- 位置：仓库根目录
- 问题：缺少 CI 配置，无法保证质量门禁
- 风险：回归不可控

5) 生产监控未完全闭环
- 位置：monitoring/
- 问题：Prometheus/Grafana 有配置但缺少明确指标落地与告警规则
- 风险：故障发现滞后

---

## P3（优化项）

1) 代码结构过于庞杂
- 位置：utils/ 下大量 "smart_*" 与 "manager" 模块
- 问题：模块边界模糊，难以维护

2) 前端 API 错误处理/重试策略不一致
- 位置：frontend/src/services/api.ts
- 问题：SSE 与普通请求失败策略不同，且重试机制较弱

3) 无统一性能基线
- 位置：tests/、monitoring/
- 问题：缺少基准压测与性能预算

---

## 生产级改造路线（建议顺序）

1) 安全基线（P0）
- 强制启用 AUTH（默认生产强制）
- 立即删除 .env 中真实密钥并完成密钥轮换
- 将用户、token 黑名单迁移到数据库或 Redis
- 限制 CORS 与添加安全头
- 禁止暴露内部端口，更新默认账号密码

2) 部署基线
- Dockerfile 增加前端构建与多阶段构建
- 引入 Python/Node 依赖锁定文件
- 配置日志轮转与集中式日志

3) 架构与稳定性
- 统一限流策略（网关 + 应用层）
- 引入数据库迁移工具
- 为 SSE 端点配置反向代理规则

4) 可观测性与质量
- 增加关键指标与告警
- 建立 CI（测试、lint、类型检查）
- 增加压测与容量评估

---

## 关键问题证据路径
- /Users/gongfan/juben/main.py
- /Users/gongfan/juben/.env
- /Users/gongfan/juben/apis/auth/api_routes_auth.py
- /Users/gongfan/juben/utils/jwt_auth.py
- /Users/gongfan/juben/nginx.conf
- /Users/gongfan/juben/Dockerfile
- /Users/gongfan/juben/docker-compose.yml
- /Users/gongfan/juben/middleware/cors_middleware.py
- /Users/gongfan/juben/requirements.txt
- /Users/gongfan/juben/frontend/package.json
- /Users/gongfan/juben/frontend/node_modules
- /Users/gongfan/juben/utils/logger_config.py
- /Users/gongfan/juben/init_database.py

---

## 建议下一步交付清单（可落地）

1) 安全整改包
- 删除 .env 实际密钥并强制轮换
- 生产环境启动前强校验 AUTH_ENABLED 与 JWT_SECRET
- 统一 CORS 与安全头策略

2) 构建部署包
- 多阶段 Dockerfile，前端构建产物进入 backend
- 引入 pip-compile 或 Poetry/uv 锁定依赖

3) 可靠性提升包
- Redis 持久化 token 黑名单
- 统一限流（用户 + IP + 端点）
- SSE 专用 Nginx 规则（禁缓冲/禁 gzip）

4) 监控与质量包
- Prometheus 指标埋点 + Grafana Dashboard
- CI 测试 + 类型检查 + lint

---

如果需要，我可以按优先级逐项落地修复与改造，先从安全与部署基线开始。
