from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/test')
def test_page():
    return render_template('test_run.html')


@main_bp.route('/logs')
def logs_page():
    return render_template('test_logs.html')


@main_bp.route('/settings')
def settings_page():
    return render_template('config_settings.html')


@main_bp.route('/init')
def init_page():
    return render_template('initialization.html')
