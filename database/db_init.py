"""
数据库初始化脚本

提供数据库表的创建和删除功能。
应用启动时会通过 app/__init__.py 中的 db.create_all() 自动建表，
此模块可用于手动管理数据库迁移。
"""

import os


def init_database(app):
    """
    初始化数据库，创建所有表（如果不存在）。

    在应用启动时自动调用，确保数据库结构完整。

    Args:
        app: Flask 应用实例
    """
    from app import db
    db.init_app(app)

    with app.app_context():
        db.create_all()
        app.logger.info('Database tables created successfully.')


def drop_database(app):
    """
    删除数据库中所有表（危险操作！）。

    仅用于开发环境重置，生产环境请勿调用。

    Args:
        app: Flask 应用实例
    """
    from app import db
    with app.app_context():
        db.drop_all()
        app.logger.warning('All database tables dropped.')
