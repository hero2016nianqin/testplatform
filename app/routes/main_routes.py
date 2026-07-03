"""
前端页面路由模块

负责渲染 HTML 模板页面，提供测试平台的用户操作界面。
每个路由对应一个功能页面，通过 Jinja2 模板引擎渲染。
"""

from flask import Blueprint, render_template

# 前端页面蓝图，无 URL 前缀（所有页面路径直接挂载在根路径下）
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页 - 系统状态仪表盘"""
    return render_template('index.html')


@main_bp.route('/test')
def test_page():
    """测试执行页面 - 显示测试项列表，支持实测值输入和实时进度"""
    return render_template('test_run.html')


@main_bp.route('/logs')
def logs_page():
    """日志查询页面 - 支持按条件搜索、导出和上传日志"""
    return render_template('test_logs.html')


@main_bp.route('/settings')
def settings_page():
    """参数设置页面 - 管理测试项、导入/导出配置方案"""
    return render_template('config_settings.html')


@main_bp.route('/init')
def init_page():
    """系统初始化页面 - 初始化示例数据、重置系统、导入默认配置"""
    return render_template('initialization.html')
