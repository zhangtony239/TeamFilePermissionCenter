# 前端镜像：多阶段构建（node 构建 -> nginx 托管 + 反代）
# build 阶段
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY . .

# 关键：build 时注入相对 API 地址，前端与后端同源（均经 5173 端口的 nginx）
# 这样浏览器请求 /api/v1/... -> nginx 反代到 server:8000，无需 CORS、无需知道服务器 IP
ARG VITE_API_BASE=/api/v1
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# 运行阶段
FROM nginx:1.27-alpine

# 处理 Windows 检出的 CRLF，保持配置干净
RUN sed -i 's/\r$//' /etc/nginx/conf.d/default.conf 2>/dev/null || true

COPY nginx.conf /etc/nginx/conf.d/default.conf

# 前端构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# Django collectstatic 静态资源（由 docker-compose 共享卷挂载到 /srv/django-static）
RUN mkdir -p /srv/django-static

EXPOSE 5173
