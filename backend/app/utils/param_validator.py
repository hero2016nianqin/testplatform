import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ParseResult(BaseModel):
    passed: bool
    normalized: Any = None
    error: Optional[str] = None


FORMAT_TYPES = {"number", "range", "percent", "enum", "expr", "array", "text"}


class FormatValidator:
    @staticmethod
    def validate_format_type(format_type: str) -> bool:
        return format_type in FORMAT_TYPES

    @staticmethod
    def validate_param_value(format_type: str, param_value: Any, enum_options: Optional[List[str]] = None) -> List[str]:
        errors: List[str] = []
        s = str(param_value) if param_value is not None else ""

        if format_type == "number":
            try:
                float(s)
            except ValueError:
                errors.append(f"format_type=number 要求数值，得到: {param_value}")

        elif format_type == "range":
            match = re.match(r'^-?\d+(\.\d+)?\s*~\s*-?\d+(\.\d+)?$', s)
            if not match:
                errors.append(f"format_type=range 要求 'min~max' 格式，得到: {param_value}")

        elif format_type == "percent":
            try:
                v = float(s.replace('%', '').replace(',', ''))
                if not (0 <= v <= 100):
                    errors.append(f"百分比值须在 0-100 之间，得到: {param_value}")
            except ValueError:
                errors.append(f"format_type=percent 要求数值，得到: {param_value}")

        elif format_type == "enum":
            if enum_options and s not in enum_options:
                errors.append(f"format_type=enum 值不在可选范围: {param_value}，可选值: {enum_options}")

        elif format_type == "expr":
            if not re.match(r'^[a-zA-Z0-9\s\+\-\*\/\(\)\.\%\_]+$', s):
                errors.append(f"format_type=expr 包含非法字符: {param_value}")

        elif format_type == "array":
            if not s.strip():
                errors.append(f"format_type=array 不能为空")

        elif format_type == "text":
            pass

        else:
            errors.append(f"不支持的 format_type: {format_type}")

        return errors

    @staticmethod
    def validate_params(params: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        fmt = params.get("format_type", "")
        if not FormatValidator.validate_format_type(fmt):
            errors.append(f"不支持的 format_type: {fmt}")
            return errors

        value = params.get("param_value")
        enum_options = params.get("enum_options")
        errs = FormatValidator.validate_param_value(fmt, value, enum_options)
        errors.extend(errs)
        return errors


class ParamParser:
    @staticmethod
    def parse(value: Any, format_type: str, params: Dict[str, Any]) -> ParseResult:
        s = str(value) if value is not None else ""

        if format_type == "number":
            try:
                v = float(s)
                return ParseResult(passed=True, normalized=v)
            except ValueError:
                return ParseResult(passed=False, error=f"数值解析失败: {value}")

        elif format_type == "range":
            match = re.match(r'^(-?\d+\.?\d*)\s*~\s*(-?\d+\.?\d*)$', s)
            if not match:
                return ParseResult(passed=False, error="区间格式错误")
            low, high = float(match.group(1)), float(match.group(2))
            try:
                v = float(params.get("param_value", 0))
            except ValueError:
                return ParseResult(passed=False, error="参数值非数值")
            passed = low <= v <= high
            return ParseResult(passed=passed, normalized={"min": low, "max": high, "value": v})

        elif format_type == "percent":
            try:
                v = float(s.replace('%', '').replace(',', ''))
                if not (0 <= v <= 100):
                    return ParseResult(passed=False, error="百分比须在 0-100 之间")
                return ParseResult(passed=True, normalized=v / 100)
            except ValueError:
                return ParseResult(passed=False, error="百分比解析失败")

        elif format_type == "enum":
            enum_options = params.get("enum_options", [])
            passed = s in enum_options
            return ParseResult(passed=passed, normalized=s,
                               error=None if passed else f"值不在枚举范围: {s}")

        elif format_type == "expr":
            return ParseResult(passed=True, normalized=s)

        elif format_type == "array":
            items = [x.strip() for x in s.split(",") if x.strip()]
            return ParseResult(passed=len(items) > 0, normalized=items)

        elif format_type == "text":
            return ParseResult(passed=True, normalized=s)

        return ParseResult(passed=False, error=f"未知 format_type: {format_type}")