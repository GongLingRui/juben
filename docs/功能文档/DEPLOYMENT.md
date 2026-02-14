# Juben 部署运维手册

> 版本: v1.0
> 更新日期: 2026-02-03
> 作者: Juben Team

---

## 目录

1. [环境准备](#1-环境准备)
2. [本地部署](#2-本地部署)
3. [Docker部署](#3-docker部署)
4. [生产部署](#4-生产部署)
5. [监控运维](#5-监控运维)
6. [备份恢复](#6-备份恢复)
7. [性能调优](#7-性能调优)

---

## 1. 环境准备

### 1.1 系统要求

**最低配置**:
- CPU: 2核心
- 内存: 4GB
- 存储: 20GB SSD
- 操作系统: Linux/macOS/Windows

**推荐配置**:
- CPU: 4核心+
- 内存: 8GB+
- 存储: 50GB SSD
- 操作系统: Ubuntu 20.04+ / CentOS 8+

### 1.2 软件依赖

| 软件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.9+ | 运行环境 |
| Docker | 20.10+ | 容器化 |
| Docker Compose | 2.0+ | 容器编排 |
| Nginx | 1.18+ | 反向代理 |
| Git | 2.0+ | 版本控制 |

### 1.3 环境变量

创建 `.env` 文件:

```bash
# LLM配置
ZHIPU_API_KEY=your_zhipu_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
OPENAI_API_KEY=your_openai_api_key

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=juben
POSTGRES_USER=juben
POSTGRES_PASSWORD=change_this_postgres_password
POSTGRES_SSLMODE=disable

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530

# JWT配置
JWT_SECRET_KEY=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 应用配置
ENVIRONMENT=production
LOG_LEVEL=INFO
ENABLE_THOUGHT_STREAMING=true
MAX_REQUEST_SIZE=10485760

# CORS配置
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 2. 本地部署

### 2.1 克隆项目

```bash
git clone https://github.com/your-org/juben.git
cd juben
```

### 2.2 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 2.3 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 配置数据库

**PostgreSQL**:
1. 访问 https://postgresql.com
2. 创建新项目
3. 获取API凭证
4. 执行SQL初始化脚本

**Redis**:
```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt install redis-server
sudo systemctl start redis

# Windows
# 下载 Redis for Windows
```

**Milvus**:
```bash
# 使用Docker运行Milvus
docker run -d \
  --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  -v ${PWD}/volumes/milvus:/var/lib/milvus \
  milvusdb/milvus:latest
```

### 2.5 运行应用

```bash
# 启动API服务
uvicorn apis.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用Python
python -m apis.main
```

### 2.6 验证部署

```bash
# 健康检查
curl http://localhost:8000/juben/health

# 查看API文档
open http://localhost:8000/docs
```

---

## 3. Docker部署

### 3.1 构建镜像

```bash
docker build -t juben-api:latest .
```

### 3.2 使用Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### 3.3 Docker Compose配置

```yaml
version: '3.8'

services:
  juben-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
      - ./outputs:/app/outputs
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    restart: unless-stopped

  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
      - "9091:9091"
    environment:
      - ETCD_ENDPOINTS=etcd:2379
      - MINIO_ADDRESS=minio:9000
    depends_on:
      - etcd
      - minio
    restart: unless-stopped

  etcd:
    image: quay.io/coreos/etcd:latest
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
    volumes:
      - etcd-data:/etcd
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - juben-api
    restart: unless-stopped

volumes:
  redis-data:
  etcd-data:
  minio-data:
  prometheus-data:
  grafana-data:
```

---

## 4. 生产部署

### 4.1 Nginx配置

**nginx.conf**:
```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # 上游服务器
    upstream juben_api {
        least_conn;
        server juben-api:8000 max_fails=3 fail_timeout=30s;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL证书
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # SSL配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # 请求限制
        client_max_body_size 10M;
        client_body_timeout 60s;

        # API路由
        location /juben/ {
            proxy_pass http://juben_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;

            # 流式响应支持
            proxy_buffering off;
            proxy_cache off;
        }

        # 静态文件
        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 4.2 系统服务配置

**systemd服务** (`/etc/systemd/system/juben.service`):
```ini
[Unit]
Description=Juben API Service
After=network.target

[Service]
Type=simple
User=juben
WorkingDirectory=/opt/juben
Environment="PATH=/opt/juben/venv/bin"
ExecStart=/opt/juben/venv/bin/gunicorn apis.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/juben/access.log \
    --error-logfile /var/log/juben/error.log \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启用服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable juben
sudo systemctl start juben
sudo systemctl status juben
```

### 4.3 负载均衡

**多实例配置**:
```nginx
upstream juben_api {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}
```

### 4.4 健康检查

**Docker健康检查**:
```yaml
services:
  juben-api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/juben/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Nginx健康检查**:
```nginx
location /health {
    proxy_pass http://juben_api/juben/health;
    access_log off;
}
```

---

## 5. 监控运维

### 5.1 Prometheus监控

**访问Prometheus**:
- URL: http://your-server:9090
- 默认用户名: admin
- 默认密码: admin

**关键指标**:
```promql
# API请求率
rate(http_requests_total[5m])

# API错误率
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# P95响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Agent调用次数
sum by(agent_name) (agent_requests_total)

# LLM响应时间
histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m]))

# 缓存命中率
cache_hits_total / (cache_hits_total + cache_misses_total)
```

### 5.2 Grafana仪表板

**访问Grafana**:
- URL: http://your-server:3000
- 默认用户名: admin
- 默认密码: admin

**推荐仪表板**:
1. API性能仪表板
2. Agent调用仪表板
3. 系统资源仪表板
4. 业务指标仪表板

### 5.3 日志管理

**日志轮转** (`/etc/logrotate.d/juben`):
```
/var/log/juben/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 juben juben
    sharedscripts
    postrotate
        systemctl reload juben > /dev/null 2>&1 || true
    endscript
}
```

**集中式日志**:
```bash
# 使用ELK Stack
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.0.0

docker run -d \
  --name logstash \
  --link elasticsearch \
  -p 5000:5000 \
  logstash:8.0.0 \
  -f /path/to/logstash.conf

docker run -d \
  --name kibana \
  --link elasticsearch \
  -p 5601:5601 \
  kibana:8.0.0
```

### 5.4 告警通知

**Prometheus告警配置**:
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'webhook'

receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'https://your-webhook-url/alert'
```

**钉钉告警**:
```python
# 钉钉WebHook告警
import requests

def send_dingtalk_alert(webhook_url, message):
    data = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    requests.post(webhook_url, json=data)
```

---

## 6. 备份恢复

### 6.1 数据库备份

**PostgreSQL备份**:
```bash
# 使用pg_dump
pg_dump -h db.xxx.postgresql.co \
  -U postgres \
  -d postgres \
  -c \
  -f backup_$(date +%Y%m%d).sql

# 或使用PostgreSQL CLI
postgresql db dump -f backup_$(date +%Y%m%d).sql
```

**自动备份脚本**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/postgresql"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/juben_backup_$TIMESTAMP.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB \
  -c \
  -f $BACKUP_FILE

# 压缩备份
gzip $BACKUP_FILE

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

**定时备份** (crontab):
```
0 2 * * * /opt/scripts/backup.sh
```

### 6.2 Redis备份

**RDB快照**:
```bash
# 触发RDB快照
redis-cli BGSAVE

# 备份RDB文件
cp /var/lib/redis/dump.rdb /backup/redis/dump_$(date +%Y%m%d).rdb
```

**AOF持久化**:
```bash
# redis.conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
```

### 6.3 文件备份

**Agent输出备份**:
```bash
#!/bin/bash
# backup_outputs.sh

OUTPUT_DIR="/opt/juben/outputs"
BACKUP_DIR="/backup/outputs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建备份
tar -czf $BACKUP_DIR/outputs_$TIMESTAMP.tar.gz $OUTPUT_DIR

# 上传到云存储
# aws s3 cp $BACKUP_DIR/outputs_$TIMESTAMP.tar.gz s3://backups/juben/
```

### 6.4 恢复流程

**PostgreSQL恢复**:
```bash
# 恢复数据库
psql -h db.xxx.postgresql.co \
  -U postgres \
  -d postgres \
  -f backup_20240203.sql
```

**Redis恢复**:
```bash
# 停止Redis
redis-cli SHUTDOWN

# 复制备份文件
cp /backup/redis/dump_20240203.rdb /var/lib/redis/dump.rdb

# 启动Redis
redis-server /etc/redis/redis.conf
```

---

## 7. 性能调优

### 7.1 应用层优化

**Worker数量**:
```python
# gunicorn配置
workers = (2 * CPU核心数) + 1

# 对于CPU密集型任务
workers = CPU核心数

# 对于IO密集型任务
workers = (2 * CPU核心数) + 1
```

**内存限制**:
```python
# 限制每个worker的内存
--max-requests 1000
--max-requests-jitter 100
```

### 7.2 数据库优化

**PostgreSQL连接池**:
```python
# connection_pool_size
settings.DATABASES['default']['CONN_MAX_AGE'] = 600
settings.DATABASES['default']['OPTIONS'] = {
    'pool_size': 20,
    'max_overflow': 10
}
```

**索引优化**:
```sql
-- 添加索引
CREATE INDEX idx_chat_messages_user_session
ON chat_messages(user_id, session_id, created_at DESC);

CREATE INDEX idx_token_usage_user_date
ON token_usage(user_id, created_at);
```

### 7.3 缓存优化

**Redis缓存策略**:
```python
# 设置合理的过期时间
await redis.set(key, value, ex=3600)  # 1小时

# 使用LRU淘汰策略
maxmemory-policy allkeys-lru
```

**多级缓存**:
```python
class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l2_cache = redis_client  # Redis缓存
        self.l3_cache = db_client  # 数据库

    async def get(self, key):
        # L1
        if key in self.l1_cache:
            return self.l1_cache[key]

        # L2
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value

        # L3
        value = await self.l3_cache.get(key)
        if value:
            await self.l2_cache.set(key, value, ex=3600)
            self.l1_cache[key] = value
            return value

        return None
```

### 7.4 网络优化

**TCP优化**:
```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 8192
net.core.netdev_max_backlog = 16384

net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000
```

**Keep-Alive优化**:
```nginx
# nginx.conf
keepalive_timeout 65;
keepalive_requests 100;
```

---

## 附录

### A. 常用命令

```bash
# 查看日志
docker-compose logs -f juben-api

# 重启服务
docker-compose restart juben-api

# 查看容器状态
docker-compose ps

# 进入容器
docker-compose exec juben-api bash

# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a
```

### B. 故障排查

参见 [故障排除指南](./TROUBLESHOOTING.md)

### C. 相关文档

- [架构设计文档](./ARCHITECTURE.md)
- [API使用指南](./API_GUIDE.md)
- [Agent开发指南](./AGENT_DEVELOPMENT.md)
