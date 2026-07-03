#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

    print(f'Starting Test Platform on {host}:{port} (debug={debug})')
    print(f'Open http://127.0.0.1:{port} in your browser')

    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
