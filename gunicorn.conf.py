"""
Gunicorn 配置 — 生产环境使用

启动方式:
    gunicorn -c gunicorn.conf.py run:app

或直接在 docker-compose 中通过 CMD 传入参数。
"""

import multiprocessing

# ── Server Socket ─────────────────────────────────────────
bind = '0.0.0.0:5000'

# ── Worker 配置 ──────────────────────────────────────────
# eventlet 支持异步并发，一个 worker 可处理数百并发连接
worker_class = 'eventlet'
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐公式
worker_connections = 2000  # eventlet 最大并发连接数
timeout = 120
keepalive = 5

# ── 日志 ─────────────────────────────────────────────────
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# ── 进程名 ───────────────────────────────────────────────
proc_name = 'test_platform'

# ── 重启 ─────────────────────────────────────────────────
max_requests = 10000        # 每个 worker 处理 1 万请求后重启（防内存泄漏）
max_requests_jitter = 1000  # 随机抖动，避免同时重启
