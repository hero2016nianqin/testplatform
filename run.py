#!/usr/bin/env python3
"""
测试平台启动入口

通过 Flask + SocketIO 启动开发服务器。
生产环境建议使用 gunicorn + eventlet 作为 WSGI 服务器。
"""

import os
import sys

# 将项目根目录添加到 Python 模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio

# 创建 Flask 应用实例
app = create_app()

if __name__ == '__main__':
    # 从环境变量读取启动参数，提供默认值方便开发
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print(f'Starting Test Platform on {host}:{port} (debug={debug})')
    print(f'Open http://127.0.0.1:{port} in your browser')

    # 启动 SocketIO 开发服务器（支持 WebSocket 实时通信）
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
