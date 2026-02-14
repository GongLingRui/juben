# Juben 故障排除指南

> 版本: v1.0
> 更新日期: 2026-02-03
> 作者: Juben Team

---

## 目录

1. [常见问题](#1-常见问题)
2. [诊断工具](#2-诊断工具)
3. [错误排查](#3-错误排查)
4. [性能问题](#4-性能问题)
5. [数据问题](#5-数据问题)
6. [网络问题](#6-网络问题)

---

## 1. 常见问题

### 1.1 启动问题

**问题**: 服务无法启动

**可能原因**:
1. 端口被占用
2. 环境变量未配置
3. 依赖未安装
4. 数据库连接失败

**解决方案**:
```bash
# 1. 检查端口占用
lsof -i :8000
netstat -tunlp | grep 8000

# 2. 检查环境变量
env | grep -E "(POSTGRES|REDIS|MILVUS|JWT)"

# 3. 检查依赖
pip list | grep -E "(fastapi|uvicorn|asyncpg)"

# 4. 测试数据库连接
python -c "from utils.database_client import test_connection; import asyncio; asyncio.run(test_connection())"
```

### 1.2 认证问题

**问题**: JWT认证失败

**错误信息**:
```
401 Unauthorized
{"detail": "Invalid token"}
```

**排查步骤**:
```bash
# 1. 检查令牌是否过期
echo "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MD..." | jq -R 'split(".") | .[1] | @base64d | fromjson | .exp'

# 2. 检查JWT配置
echo $JWT_SECRET_KEY

# 3. 生成新令牌
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}'
```

### 1.3 LLM调用问题

**问题**: LLM API调用失败

**错误信息**:
```
LLM调用失败: Connection timeout
```

**排查步骤**:
```python
# 测试LLM连接
import asyncio
from utils.llm_client import get_llm_client

async def test_llm():
    client = get_llm_client("zhipu")
    messages = [{"role": "user", "content": "测试"}]
    try:
        response = await client.chat(messages)
        print(f"成功: {response}")
    except Exception as e:
        print(f"失败: {e}")

asyncio.run(test_llm())
```

### 1.4 数据库连接问题

**问题**: 无法连接到数据库

**错误信息**:
```
Database connection failed: connection refused
```

**排查步骤**:
```bash
# PostgreSQL连接测试
pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER

# Redis连接测试
redis-cli ping

# Milvus连接测试
curl $MILVUS_HOST:$MILVUS_PORT/healthz
```

---

## 2. 诊断工具

### 2.1 健康检查脚本

```bash
#!/bin/bash
# health_check.sh

echo "=== Juben健康检查 ==="

# API健康检查
echo -n "API服务: "
if curl -sf http://localhost:8000/juben/health > /dev/null; then
    echo "✅ 正常"
else
    echo "❌ 异常"
fi

# Redis检查
echo -n "Redis服务: "
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 异常"
fi

# PostgreSQL检查
echo -n "PostgreSQL服务: "
if pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 异常"
fi

# Milvus检查
echo -n "Milvus服务: "
if curl -sf $MILVUS_HOST:$MILVUS_PORT/healthz > /dev/null 2>&1; then
    echo "✅ 正常"
else
    echo "❌ 异常"
fi

echo "=== 检查完成 ==="
```

### 2.2 日志分析脚本

```bash
#!/bin/bash
# analyze_logs.sh

LOG_FILE="/var/log/juben/error.log"

echo "=== 错误日志分析 ==="

# 统计错误类型
echo "错误类型统计:"
grep -i "error" $LOG_FILE | awk -F':' '{print $3}' | sort | uniq -c | sort -rn

# 最近1小时的错误
echo -e "\n最近1小时错误:"
grep -i "$(date -d '1 hour ago' '+%Y-%m-%d %H')" $LOG_FILE | tail -10

# 统计错误频率
echo -e "\n错误频率:"
grep -i "error" $LOG_FILE | awk '{print $1}' | uniq -c

echo "=== 分析完成 ==="
```

### 2.3 性能诊断

```python
# performance_diagnostics.py
import asyncio
import time
from utils.llm_client import get_llm_client
from utils.database_client import get_postgresql_client
from utils.redis_client import get_redis_client

async def diagnose_performance():
    """性能诊断"""
    print("=== 性能诊断 ===")

    # LLM响应时间
    print("\n1. LLM响应时间:")
    client = get_llm_client("zhipu")
    messages = [{"role": "user", "content": "测试"}]

    start = time.time()
    await client.chat(messages)
    duration = time.time() - start
    print(f"   响应时间: {duration:.2f}s")

    # 数据库查询时间
    print("\n2. 数据库查询时间:")
    db = get_postgresql_client()

    start = time.time()
    db.table('chat_messages').select('id').limit(1).execute()
    duration = time.time() - start
    print(f"   查询时间: {duration:.3f}s")

    # Redis响应时间
    print("\n3. Redis响应时间:")
    redis = await get_redis_client()

    start = time.time()
    await redis.ping()
    duration = time.time() - start
    print(f"   Ping时间: {duration:.3f}s")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    asyncio.run(diagnose_performance())
```

---

## 3. 错误排查

### 3.1 HTTP错误

**4xx错误**:
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求格式和必填字段 |
| 401 | 未授权 | 检查JWT令牌是否有效 |
| 403 | 权限不足 | 检查用户权限配置 |
| 404 | 资源不存在 | 确认API端点正确 |
| 429 | 请求过于频繁 | 降低请求频率 |

**5xx错误**:
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 500 | 服务器内部错误 | 查看服务器日志 |
| 502 | 网关错误 | 检查上游服务状态 |
| 503 | 服务不可用 | 检查服务负载 |
| 504 | 网关超时 | 增加超时时间 |

### 3.2 Agent错误

**问题**: Agent执行失败

**排查**:
```python
# 检查Agent状态
from agents.agent_registry import AgentRegistry

agent = AgentRegistry.get_agent("short_drama_planner_agent")
print(agent.get_agent_info())
print(agent.get_performance_info())
```

**问题**: Agent超时

**解决方案**:
```python
# 增加超时时间
async def process_with_timeout(request_data, timeout=300):
    try:
        async with asyncio.timeout(timeout):
            result = await agent.process_request(request_data)
    except asyncio.TimeoutError:
        print("Agent执行超时")
```

### 3.3 数据库错误

**问题**: 数据库查询失败

**排查**:
```bash
# 检查数据库连接
psql -h db.xxx.postgresql.co -U postgres -d postgres

# 检查表结构
psql -h db.xxx.postgresql.co -U postgres -d postgres \
  -c "\d chat_messages"

# 检查索引
psql -h db.xxx.postgresql.co -U postgres -d postgres \
  -c "\d+ chat_messages"
```

**问题**: 连接池耗尽

**解决方案**:
```python
# 增加连接池大小
# settings.py
DATABASES = {
    'default': {
        'OPTIONS': {
            'pool_size': 30,  # 增加连接池
            'max_overflow': 20
        }
    }
}
```

---

## 4. 性能问题

### 4.1 API响应慢

**诊断**:
```bash
# 查看慢查询
grep "duration" /var/log/juben/access.log | awk '$NF > 1.0'

# 使用Prometheus查询
# P95响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**解决方案**:
1. 启用缓存
2. 优化数据库查询
3. 增加Worker数量
4. 使用CDN加速

### 4.2 LLM响应慢

**诊断**:
```python
import time
from utils.llm_client import get_llm_client

async def benchmark_llm():
    client = get_llm_client("zhipu")
    messages = [{"role": "user", "content": "测试"}]

    times = []
    for i in range(10):
        start = time.time()
        await client.chat(messages)
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    print(f"平均响应时间: {avg_time:.2f}s")
    print(f"最快: {min(times):.2f}s")
    print(f"最慢: {max(times):.2f}s")
```

**解决方案**:
1. 切换到更快的模型
2. 减少Token数量
3. 使用批处理
4. 启用流式响应

### 4.3 内存泄漏

**诊断**:
```bash
# 查看内存使用
docker stats juben-api

# 内存分析
pip install memory_profiler
python -m memory_profiler apis/main.py
```

**解决方案**:
1. 定期重启Worker
2. 限制请求大小
3. 使用连接池
4. 释放未使用的资源

---

## 5. 数据问题

### 5.1 数据丢失

**恢复步骤**:
```bash
# 1. 停止服务
docker-compose stop juben-api

# 2. 恢复数据库
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB \
  -f /backup/postgresql/backup_20240203.sql

# 3. 恢复Redis
redis-cli --rdb /backup/redis/dump_20240203.rdb

# 4. 重启服务
docker-compose start juben-api
```

### 5.2 数据不一致

**诊断**:
```sql
-- 检查孤立记录
SELECT user_id, COUNT(*) FROM chat_messages
GROUP BY user_id
HAVING COUNT(*) < 5;

-- 检查异常Token使用
SELECT user_id, SUM(total_tokens)
FROM token_usage
GROUP BY user_id
HAVING SUM(total_tokens) > 100000;
```

### 5.3 缓存不一致

**清理方案**:
```bash
# 清理Redis缓存
redis-cli FLUSHDB

# 或清理特定键
redis-cli --scan --pattern "session:*" | xargs redis-cli DEL

# 重建缓存
python scripts/rebuild_cache.py
```

---

## 6. 网络问题

### 6.1 连接超时

**诊断**:
```bash
# 测试网络连通性
ping -c 4 db.xxx.postgresql.co
traceroute db.xxx.postgresql.co

# 测试端口连通性
nc -zv db.xxx.postgresql.co 5432
telnet db.xxx.postgresql.co 5432
```

**解决方案**:
1. 检查防火墙规则
2. 增加超时时间
3. 使用连接池
4. 启用重试机制

### 6.2 DNS解析问题

**诊断**:
```bash
# 检查DNS解析
nslookup db.xxx.postgresql.co
dig db.xxx.postgresql.co

# 检查/etc/hosts
cat /etc/hosts | grep postgresql
```

**解决方案**:
```bash
# 添加DNS缓存
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# 或直接使用IP
export POSTGRES_HOST="IP"
```

### 6.3 SSL证书问题

**诊断**:
```bash
# 检查SSL证书
openssl s_client -connect db.xxx.postgresql.co:5432 -showcerts

# 检查证书有效期
echo | openssl s_client -connect api.openai.com:443 2>/dev/null | \
  openssl x509 -noout -dates
```

**解决方案**:
```python
# 禁用SSL验证 (仅用于测试)
import ssl
import httpx

client = httpx.Client(verify=False)
```

---

## 附录

### A. 调试模式

**启用调试日志**:
```bash
export LOG_LEVEL=DEBUG
python -m apis.main
```

**使用pdb调试**:
```python
import pdb; pdb.set_trace()

# 或使用ipdb
import ipdb; ipdb.set_trace()
```

### B. 日志位置

| 日志类型 | 位置 |
|----------|------|
| 应用日志 | `/var/log/juben/` |
| Nginx日志 | `/var/log/nginx/` |
| Docker日志 | `docker-compose logs` |
| 系统日志 | `/var/log/syslog` |

### C. 获取帮助

- GitHub Issues: https://github.com/your-org/juben/issues
- 文档: https://docs.juben.example.com
- 邮件: support@juben.example.com

### D. 相关文档

- [架构设计文档](./ARCHITECTURE.md)
- [API使用指南](./API_GUIDE.md)
- [Agent开发指南](./AGENT_DEVELOPMENT.md)
- [部署运维手册](./DEPLOYMENT.md)
