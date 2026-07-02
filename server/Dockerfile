# 后端镜像：Django + Gunicorn
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

WORKDIR /app

# psycopg[binary] 运行时需要 libpq；pypdf 为纯 Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app/

# 处理 Windows 检出可能产生的 CRLF，并赋予执行权限
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker-entrypoint.sh"]
CMD ["gunicorn", "tfpc.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
