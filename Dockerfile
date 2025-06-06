# 使用官方Python运行时作为基础镜像
FROM python:3.9-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml .
COPY main.py .

# 安装Python依赖
RUN pip install --no-cache-dir .

# 创建必要的目录
RUN mkdir -p templates static

# 复制模板文件
COPY templates/ templates/

# 生产阶段
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 从构建阶段复制安装的包
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用文件
COPY --from=builder /app .

# 创建目录并设置权限
RUN mkdir -p templates static && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口（默认8000，可通过环境变量覆盖）
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# 启动命令
CMD ["python", "main.py"] 