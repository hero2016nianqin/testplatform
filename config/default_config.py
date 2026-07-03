import os


class DefaultConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'test-platform-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'sqlite:///' + os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     'database', 'test_platform.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'uploads')
    LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              'logs')

    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Shanghai'

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'json', 'xml', 'yaml', 'yml'}
