import os
import json
import gzip
import shutil
from datetime import datetime
from typing import List, Optional


class LogService:
    def __init__(self, log_folder: str):
        self.log_folder = log_folder
        os.makedirs(log_folder, exist_ok=True)

    def save_log(self, batch_id: str, log_data: dict) -> str:
        date_str = datetime.utcnow().strftime('%Y%m%d')
        filename = f'{batch_id}_{date_str}.json'
        filepath = os.path.join(self.log_folder, filename)

        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'batch_id': batch_id,
            **log_data
        }

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

        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        start = (page - 1) * per_page
        end = start + per_page
        return results[start:end]

    def delete_log(self, batch_id: str) -> bool:
        deleted = False
        for filename in os.listdir(self.log_folder):
            if batch_id in filename:
                filepath = os.path.join(self.log_folder, filename)
                os.remove(filepath)
                deleted = True
        return deleted

    def compress_old_logs(self, days_old: int = 30):
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
