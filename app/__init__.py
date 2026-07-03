import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS

db = SQLAlchemy()
socketio = SocketIO()
cors = CORS()


def create_app(config_object=None):
    app = Flask(__name__)

    if config_object is None:
        from config.default_config import DefaultConfig
        app.config.from_object(DefaultConfig)
    else:
        app.config.from_object(config_object)

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins='*')
    cors.init_app(app)

    from app.models import TestItem, TestResult, TestConfig, TestRun
    with app.app_context():
        db.create_all()

    from app.routes.test_routes import test_bp
    from app.routes.config_routes import config_bp
    from app.routes.log_routes import log_bp
    from app.routes.init_routes import init_bp

    app.register_blueprint(test_bp, url_prefix='/api/tests')
    app.register_blueprint(config_bp, url_prefix='/api/configs')
    app.register_blueprint(log_bp, url_prefix='/api/logs')
    app.register_blueprint(init_bp, url_prefix='/api/init')

    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    from app.services.scheduler import init_scheduler
    init_scheduler(app)

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('LOG_FOLDER', 'logs'), exist_ok=True)

    return app
