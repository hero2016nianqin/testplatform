import json
import csv
import io
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional


class ConfigImportError(Exception):
    pass


class ConfigManager:
    SUPPORTED_FORMATS = {'csv', 'xlsx', 'json', 'xml'}

    @staticmethod
    def parse_import_file(file_storage, file_format: str) -> Dict[str, Any]:
        if file_format not in ConfigManager.SUPPORTED_FORMATS:
            raise ConfigImportError(
                f'Unsupported format: {file_format}. '
                f'Supported: {ConfigManager.SUPPORTED_FORMATS}'
            )

        parse_method = getattr(ConfigManager, f'_parse_{file_format}')
        return parse_method(file_storage)

    @staticmethod
    def _parse_csv(file_storage) -> Dict[str, Any]:
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
        data = json.load(file_storage)
        return {
            'format': 'json',
            'items': data if isinstance(data, list) else data.get('items', []),
            'count': len(data) if isinstance(data, list) else len(
                data.get('items', []))
        }

    @staticmethod
    def _parse_xml(file_storage) -> Dict[str, Any]:
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
        required_keys = {'name', 'expected_value', 'min_value', 'max_value'}
        validated = []
        errors = []

        for idx, item in enumerate(parsed_data.get('items', [])):
            missing = required_keys - set(item.keys())
            if missing:
                errors.append(
                    f'Row {idx + 1}: missing keys {missing}')
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
