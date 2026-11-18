# Linux 服务器部署（IP 直连方式）

项目源码托管在公开仓库：<https://github.com/Xcc682/eclass>

```bash
git clone https://github.com/Xcc682/eclass.git
cd eclass
```

项目根目录保留 `docker-compose.yml` 用于本地开发；在 Linux 服务器上部署时使用
独立的 `docker-compose.production.yml`。

## 首次部署

1. 安装 Docker Engine 与 Docker Compose 插件。
2. 将项目复制到服务器并进入项目目录（或直接使用上面的克隆命令）。
3. 创建生产环境变量文件：

   ```bash
   cp .env.production.example .env
   chmod 600 .env
   ```

4. 编辑 `.env`：将 `SERVER_PUBLIC_IP` 替换为服务器公网 IPv4 地址，
   并替换所有 `REPLACE_...` 占位值。JWT 密钥可用下列命令生成：

   ```bash
   openssl rand -hex 32
   ```

5. 构建并启动服务栈：

   ```bash
   docker compose -f docker-compose.production.yml config
   docker compose -f docker-compose.production.yml up -d --build
   docker compose -f docker-compose.production.yml ps
   ```

6. 在服务器防火墙与云厂商安全组中放行 TCP 5667 端口，然后访问
   `http://SERVER_PUBLIC_IP:5667`。

## 日常运维

```bash
# 跟踪后端日志
docker compose -f docker-compose.production.yml logs -f backend

# 在服务器本机检查就绪状态
curl http://127.0.0.1:7899/health/ready

# 拉取新代码后更新
docker compose -f docker-compose.production.yml up -d --build
```

生产栈仅将前端暴露在 HTTP 5667 端口。PostgreSQL、Redis 与 MinIO 只能通过
私有 Docker 网络在容器间访问；FastAPI 另外绑定在 `127.0.0.1:7899`，
因此只能从 Linux 服务器本机访问。

正式对外提供真实用户服务前，请补充域名与 HTTPS 反向代理。

### 排查：页面能打开但所有接口 502

症状：`http://SERVER_PUBLIC_IP:5667/` 正常返回页面，静态资源也能加载，但
`/api/v1/*`、`/health`、`/docs`、`/media/` 一律 502，浏览器控制台出现
`Unexpected token '<'`（前端把 nginx 的 502 HTML 当成 JSON 解析）。

这是 nginx 缓存了后端容器旧 IP 导致的，不是端口占用，也不是后端故障。先确认：

```bash
# nginx 实际在连哪个 IP
docker compose -f docker-compose.production.yml logs --tail=20 frontend | grep 'upstream'

# Docker DNS 现在解析到哪个 IP
docker compose -f docker-compose.production.yml exec frontend getent hosts backend
```

两个 IP 不一致即确诊。原因是 `proxy_pass http://backend:8000;` 这种写法只在
nginx 启动时解析一次域名并永久缓存，而后端容器每次重建都会拿到新 IP。

`frontend/nginx.production.conf` 已改用变量形式，使 nginx 每次请求都重新解析：

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
set $backend http://backend:8000;
# 各 location 中使用 proxy_pass $backend;
```

镜像已包含该配置，执行 `up -d --build` 重建前端即可生效。若需在运行中的容器上
临时热修而不重建镜像，备份后覆盖配置并热加载：

```bash
docker exec eclass-frontend-1 nginx -t && docker exec eclass-frontend-1 nginx -s reload
```

验证应得到 200（`/api/v1/users/profile` 无 token 时返回 401 亦属正常）：

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://SERVER_PUBLIC_IP:5667/health
curl -s -o /dev/null -w "%{http_code}\n" http://SERVER_PUBLIC_IP:5667/api/v1/interviews/scenarios
```

## 本地开发与测试

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 后端静态检查与测试
ruff check app/
python -m pytest tests/ -q

# 前端
cd frontend
npm install
npm run dev:h5          # 开发服务器，默认 5667 端口
npm run type-check      # TypeScript 类型检查
```

前端开发服务器会把 `/api` 请求代理到 `http://127.0.0.1:8000`，
因此后端需先启动。
