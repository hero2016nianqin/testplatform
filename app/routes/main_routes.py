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


@main_bp.route('/lines')
def lines_page():
    """线体列表页面"""
    return render_template('test_run.html', view='lines')


@main_bp.route('/equipment')
def equipment_page():
    """装备列表页面（含测试执行视图）"""
    return render_template('test_run.html', view='equipment')


@main_bp.route('/logs')
def logs_page():
    """日志查询页面 - 支持按条件搜索、导出和上传日志"""
    return render_template('test_logs.html')


@main_bp.route('/records')
def records_page():
    """测试记录页面 - R1/R2/R3 层级结构"""
    return render_template('test_records.html')


@main_bp.route('/releases')
def releases_page():
    """版本归档与发布页面"""
    return render_template('releases.html')


@main_bp.route('/settings')
def settings_page():
    """参数设置页面 - 管理测试项、导入/导出配置方案"""
    return render_template('config_settings.html')


@main_bp.route('/init')
def init_page():
    """系统初始化页面 - 初始化示例数据、重置系统、导入默认配置"""
    return render_template('initialization.html')


@main_bp.route('/station-settings/<int:station_id>')
def station_settings_page(station_id):
    """工站设置页面 - 装备/硬件/软件/场景参数配置"""
    return render_template('station_settings.html')
