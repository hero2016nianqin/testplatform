import os


def init_database(app):
    from app import db
    db.init_app(app)

    with app.app_context():
        db.create_all()
        app.logger.info('Database tables created successfully.')


def drop_database(app):
    from app import db
    with app.app_context():
        db.drop_all()
        app.logger.warning('All database tables dropped.')
