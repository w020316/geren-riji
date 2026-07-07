FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（gcc 用于编译部分 Python 包）
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 先拷依赖清单，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷源码
COPY . .

# 创建数据目录（云端通过持久化磁盘挂载到 /app/data）
RUN mkdir -p /app/data/chroma_db /app/data/diaries /app/data/models

EXPOSE 8000

# Render 通过 PORT 环境变量指定端口，本地默认 8000
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# 健康检查（Render 会探测此路径）
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + __import__('os').getenv('PORT', '8000') + '/api/health').read()" || exit 1

CMD ["python", "main.py"]
