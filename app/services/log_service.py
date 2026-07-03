"""
日志服务模块

提供测试日志的本地文件存储、查询、删除、压缩和统计功能。
日志以 JSON 格式按日期分文件存储，支持按批次号检索。
"""

import os
import json
import gzip
import shutil
from datetime import datetime
from typing import List, Optional


class LogService:
    """
    日志服务，管理测试日志的本地文件存储和检索。

    日志文件命名规则: {batch_id}_{yyyyMMdd}.json
    每个文件存储该批次当天的所有日志条目（JSON 数组）。
    """

    def __init__(self, log_folder: str):
        """
        Args:
            log_folder: 日志文件存储目录的绝对路径
        """
        self.log_folder = log_folder
        os.makedirs(log_folder, exist_ok=True)

    def save_log(self, batch_id: str, log_data: dict) -> str:
        """
        保存一条日志到文件。

        Args:
            batch_id: 关联的测试批次号
            log_data: 日志数据字典

        Returns:
            写入的文件路径
        """
        date_str = datetime.utcnow().strftime('%Y%m%d')
        filename = f'{batch_id}_{date_str}.json'
        filepath = os.path.join(self.log_folder, filename)

        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'batch_id': batch_id,
            **log_data
        }

        # 如果文件已存在，追加到 JSON 数组末尾；否则创建新文件
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                if isinstance(existing, list):
                    existing.append(log_entry)
                else:
                    existing = [existing, log_entry]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([log_entry], f, ensure_ascii=False, indent=2)

        return filepath

    def get_logs(self, batch_id: Optional[str] = None,
                 page: int = 1, per_page: int = 50) -> List[dict]:
        """
        查询日志，支持按批次号筛选和分页。

        Args:
            batch_id: 可选的批次号筛选
            page: 页码（从1开始）
            per_page: 每页条数

        Returns:
            日志条目列表（按时间倒序排列）
        """
        results = []
        files = sorted(os.listdir(self.log_folder), reverse=True)

        for filename in files:
            if batch_id and batch_id not in filename:
                continue
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(self.log_folder, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        results.append(data)
            except (json.JSONDecodeError, IOError):
                continue

        # 按时间戳降序排列
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        start = (page - 1) * per_page
        end = start + per_page
        return results[start:end]

    def delete_log(self, batch_id: str) -> bool:
        """
        删除指定批次的所有日志文件。

        Args:
            batch_id: 要删除的批次号

        Returns:
            是否成功删除了至少一个文件
        """
        deleted = False
        for filename in os.listdir(self.log_folder):
            if batch_id in filename:
                filepath = os.path.join(self.log_folder, filename)
                os.remove(filepath)
                deleted = True
        return deleted

    def compress_old_logs(self, days_old: int = 30):
        """
        将指定天数前的日志文件压缩为 .gz 格式以节省磁盘空间。

        Args:
            days_old: 压缩距今多少天之前的文件（默认30天）
        """
        cutoff = datetime.utcnow().timestamp() - days_old * 86400
        for filename in os.listdir(self.log_folder):
            filepath = os.path.join(self.log_folder, filename)
            if filename.endswith('.gz'):
                continue
            if os.path.getmtime(filepath) < cutoff:
                with open(filepath, 'rb') as f_in:
                    gz_path = filepath + '.gz'
                    with gzip.open(gz_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(filepath)

    def get_log_statistics(self) -> dict:
        """
        获取日志存储统计信息。

        Returns:
            包含 total_files（文件数）、total_size_bytes（总字节数）、
            total_size_mb（总MB数）、log_folder（存储路径）的字典
        """
        total_files = 0
        total_size = 0
        for filename in os.listdir(self.log_folder):
            filepath = os.path.join(self.log_folder, filename)
            if os.path.isfile(filepath):
                total_files += 1
                total_size += os.path.getsize(filepath)
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'log_folder': self.log_folder,
        }
