/**
 * 测试平台 - 前端通用工具函数
 *
 * 提供全局可用的格式化、提示、错误处理和防抖等功能。
 * 在所有页面中通过 base.html 引用加载。
 */

/**
 * 将 ISO 时间字符串格式化为本地中文时间显示
 * @param {string} isoString - ISO 8601 格式的时间字符串
 * @returns {string} 格式化后的时间字符串
 */
function formatTime(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    return d.toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
}

/**
 * 在页面右上角显示一个自动消失的 Toast 通知
 * @param {string} message - 通知内容
 * @param {string} type - 通知类型（info/success/danger/warning）
 */
function showToast(message, type) {
    type = type || 'info';
    const container = document.getElementById('toast-container');
    if (!container) {
        const div = document.createElement('div');
        div.id = 'toast-container';
        div.style.cssText = 'position: fixed; top: 70px; right: 20px; z-index: 9999;';
        document.body.appendChild(div);
    }
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

/**
 * 统一处理 API 响应，自动检查 HTTP 状态码和业务 code
 * @param {Response} response - fetch 返回的 Response 对象
 * @returns {Promise<Object>} 解析后的 JSON 数据
 * @throws {Error} HTTP 或业务错误时抛出
 */
function handleApiError(response) {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json().then(data => {
        if (data.code !== 0) {
            throw new Error(data.message || 'Unknown error');
        }
        return data;
    });
}

/**
 * 防抖函数，限制高频操作（如搜索输入）的执行频率
 * @param {Function} func - 要执行的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} 包装后的防抖函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
