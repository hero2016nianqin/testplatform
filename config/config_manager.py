"""
配置管理器模块

负责测试配置文件的解析、校验、导入和导出。
支持 CSV / XLSX / JSON / XML 四种格式，未来可通过添加 _parse_xxx 方法扩展新格式。
"""

import json
import csv
import io
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


class ConfigImportError(Exception):
    """配置文件导入时发生的异常"""
    pass


class ConfigManager:
    """配置管理器，提供文件解析、数据校验和导入导出功能"""

    # 当前支持的导入格式集合
    SUPPORTED_FORMATS = {'csv', 'xlsx', 'json', 'xml'}

    @staticmethod
    def parse_import_file(file_storage, file_format: str) -> Dict[str, Any]:
        """
        解析上传的配置文件，根据格式类型分发到对应的解析方法。

        Args:
            file_storage: Flask 上传文件对象
            file_format: 文件格式（csv/xlsx/json/xml）

        Returns:
            解析后的字典，包含 items、columns、count 等信息

        Raises:
            ConfigImportError: 不支持的格式时抛出
        """
        if file_format not in ConfigManager.SUPPORTED_FORMATS:
            raise ConfigImportError(
                f'Unsupported format: {file_format}. '
                f'Supported: {ConfigManager.SUPPORTED_FORMATS}'
            )

        parse_method = getattr(ConfigManager, f'_parse_{file_format}')
        return parse_method(file_storage)

    @staticmethod
    def _parse_csv(file_storage) -> Dict[str, Any]:
        """解析 CSV 格式的配置文件"""
        stream = io.StringIO(file_storage.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        items = list(reader)
        return {
            'format': 'csv',
            'items': items,
            'columns': reader.fieldnames,
            'count': len(items)
        }

    @staticmethod
    def _parse_xlsx(file_storage) -> Dict[str, Any]:
        """解析 Excel (XLSX) 格式的配置文件"""
        df = pd.read_excel(file_storage)
        items = df.to_dict(orient='records')
        return {
            'format': 'xlsx',
            'items': items,
            'columns': list(df.columns),
            'count': len(items)
        }

    @staticmethod
    def _parse_json(file_storage) -> Dict[str, Any]:
        """解析 JSON 格式的配置文件"""
        data = json.load(file_storage)
        return {
            'format': 'json',
            'items': data if isinstance(data, list) else data.get('items', []),
            'count': len(data) if isinstance(data, list) else len(
                data.get('items', []))
        }

    @staticmethod
    def _parse_xml(file_storage) -> Dict[str, Any]:
        """解析 XML 格式的配置文件"""
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_storage)
        root = tree.getroot()
        items = []
        for child in root:
            item = {elem.tag: elem.text for elem in child}
            items.append(item)
        return {
            'format': 'xml',
            'items': items,
            'count': len(items)
        }

    @staticmethod
    def validate_config_data(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        校验解析后的配置数据，检查必填字段和数值有效性。

        Args:
            parsed_data: parse_import_file 的返回结果

        Returns:
            包含 validated（通过项）、errors（错误项）、统计计数的字典
        """
        required_keys = {'name', 'expected_value', 'min_value', 'max_value'}
        validated = []
        errors = []

        for idx, item in enumerate(parsed_data.get('items', [])):
            missing = required_keys - set(item.keys())
            if missing:
                errors.append(f'Row {idx + 1}: missing keys {missing}')
                continue
            try:
                validated.append({
                    'name': str(item['name']).strip(),
                    'description': str(item.get('description', '')).strip(),
                    'expected_value': float(item['expected_value']),
                    'min_value': float(item['min_value']),
                    'max_value': float(item['max_value']),
                    'unit': str(item.get('unit', '')).strip(),
                    'category': str(item.get('category', 'general')).strip(),
                })
            except (ValueError, TypeError) as e:
                errors.append(f'Row {idx + 1}: invalid numeric value - {e}')

        return {
            'validated': validated,
            'errors': errors,
            'total': len(parsed_data.get('items', [])),
            'valid_count': len(validated),
            'error_count': len(errors)
        }

    @staticmethod
    def export_to_json(test_items, filepath: str):
        """将测试项列表导出为 JSON 文件"""
        data = {
            'export_time': datetime.now().isoformat(),
            'items': [
                {
                    'name': item.name,
                    'description': item.description,
                    'expected_value': item.expected_value,
                    'min_value': item.min_value,
                    'max_value': item.max_value,
                    'unit': item.unit,
                    'category': item.category,
                }
                for item in test_items
            ]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def export_to_csv(test_items, filepath: str):
        """将测试项列表导出为 CSV 文件"""
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['name', 'description', 'expected_value', 'min_value',
                 'max_value', 'unit', 'category'])
            for item in test_items:
                writer.writerow([
                    item.name, item.description, item.expected_value,
                    item.min_value, item.max_value, item.unit, item.category
                ])

    @staticmethod
    def export_to_excel(test_items, filepath: str):
        """将测试项列表导出为 Excel (XLSX) 文件"""
        data = [
            {
                'name': item.name,
                'description': item.description,
                'expected_value': item.expected_value,
                'min_value': item.min_value,
                'max_value': item.max_value,
                'unit': item.unit,
                'category': item.category,
            }
            for item in test_items
        ]
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
