from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field, field_validator


# ── Format Types ──
FORMAT_TYPES = ["number", "range", "percent", "enum", "expr", "array", "text"]


class ExtendParamSchema(BaseModel):
    param_code: str = Field(..., max_length=50)
    param_name: str = Field(..., max_length=100)
    param_value: str = Field(..., max_length=500)
    format_type: str = Field(..., pattern=r"^(number|range|percent|enum|expr|array|text)$")
    enum_options: Optional[List[str]] = None
    default_value: Optional[str] = None
    required: bool = False


class IndicatorParamsSchema(BaseModel):
    standard_value: Optional[Union[float, str]] = None
    upper_limit: Optional[Union[float, str]] = None
    lower_limit: Optional[Union[float, str]] = None
    precision: Optional[float] = None
    tolerance: Optional[float] = None
    hardware_channel: str = Field(default="")
    test_frequency: int = Field(default=1, ge=1)
    exceed_handler: str = Field(default="ALARM")
    format_type: str = Field(default="number", pattern=r"^(number|range|percent|enum|expr|array|text)$")
    extend_params: List[ExtendParamSchema] = Field(default_factory=list)


# ── Indicator Dictionary ──
class IndicatorCreateReq(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    category: str = Field(default="")
    domain: str = Field(default="", max_length=50)
    unit: str = Field(default="", max_length=20)
    hardware_model: str = Field(default="", max_length=100)
    test_rule: str = Field(default="")
    params: IndicatorParamsSchema
    description: str = Field(default="")
    remark: Optional[str] = None
    status: int = Field(default=1, ge=0, le=1)
    test_params: Optional[list] = None


class IndicatorUpdateReq(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None
    unit: Optional[str] = None
    hardware_model: Optional[str] = None
    test_rule: Optional[str] = None
    params: Optional[IndicatorParamsSchema] = None
    description: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[int] = None
    test_params: Optional[list] = None


class IndicatorResp(BaseModel):
    id: int
    code: str
    name: str
    category: str
    domain: str = ""
    unit: str
    hardware_model: Optional[str] = None
    test_rule: Optional[str] = None
    params: dict
    test_params: list = []
    status: int
    description: str
    remark: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Test Item Collection ──
class CollectionTestItemCreateReq(BaseModel):
    name: str = Field(..., max_length=100)
    process_name: str = ""
    station: str = ""
    test_type: str = ""
    sort_order: int = 0
    service_address: str = ""
    timeout_seconds: Optional[int] = Field(None, ge=1, le=86400)
    block_type: str = "normal"
    parallel_enabled: bool = False
    status: int = 1

    @field_validator("service_address")
    @classmethod
    def validate_service_address(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("微服务地址必须以 http:// 或 https:// 开头")
        return v

    @field_validator("block_type")
    @classmethod
    def validate_block_type(cls, v: str) -> str:
        allowed = {"must_test", "critical", "normal"}
        if v not in allowed:
            raise ValueError(f"阻断类型必须为: {', '.join(allowed)}")
        return v


class CollectionTestItemUpdateReq(BaseModel):
    name: Optional[str] = None
    process_name: Optional[str] = None
    station: Optional[str] = None
    test_type: Optional[str] = None
    sort_order: Optional[int] = None
    service_address: Optional[str] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=86400)
    block_type: Optional[str] = None
    parallel_enabled: Optional[bool] = None
    status: Optional[int] = None

    @field_validator("service_address")
    @classmethod
    def validate_service_address(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v and not v.startswith(("http://", "https://")):
            raise ValueError("微服务地址必须以 http:// 或 https:// 开头")
        return v

    @field_validator("block_type")
    @classmethod
    def validate_block_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"must_test", "critical", "normal"}
            if v not in allowed:
                raise ValueError(f"阻断类型必须为: {', '.join(allowed)}")
        return v


class CollectionTestItemResp(BaseModel):
    id: int
    collection_id: int
    name: str
    process_name: str = ""
    station: str = ""
    test_type: str
    sort_order: int
    service_address: str = ""
    timeout_seconds: Optional[int] = None
    block_type: str = "normal"
    parallel_enabled: bool = False
    status: int = 1
    item_revision: int = 0
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    owner_manual: bool = False
    domain: str = ""


class CollectionTestItemOwnerUpdateReq(BaseModel):
    owner_name: str = Field(default="", max_length=100)


class CollectionCreateReq(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    product_type: str = ""
    description: str = ""


class CollectionUpdateReq(BaseModel):
    name: Optional[str] = None
    product_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class CollectionResp(BaseModel):
    id: int
    name: str
    code: str
    product_type: str
    description: str
    status: int
    version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── BOM Config ──
class BomConfigCreateReq(BaseModel):
    bom_code: str = Field(..., max_length=100)
    bom_name: str = ""
    collection_id: int


class BomConfigUpdateReq(BaseModel):
    bom_code: Optional[str] = None
    bom_name: Optional[str] = None
    collection_id: Optional[int] = None
    status: Optional[int] = None


class BomConfigResp(BaseModel):
    id: int
    bom_code: str
    bom_name: str
    collection_id: int
    collection_version: int = 1
    status: int
    version: int
    review_status: str = "none"
    review_comment: Optional[str] = None
    review_operator: Optional[str] = None
    reviewed_at: Optional[str] = None
    archived: bool = False
    archived_at: Optional[str] = None
    domain_owners: dict = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── BOM Indicator ──
class BomIndicatorCreateReq(BaseModel):
    indicator_id: int
    unit: str = ""
    judgment_rule: str = "合格"
    test_stage: str = ""
    remark: str = ""
    params: Optional[list] = None


class BomIndicatorBatchCreateReq(BaseModel):
    indicators: List[BomIndicatorCreateReq]


class BomIndicatorUpdateReq(BaseModel):
    unit: Optional[str] = None
    judgment_rule: Optional[str] = None
    test_stage: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[int] = None
    params: Optional[list] = None
    # 乐观锁：所属测试项 id 与客户端持有的版本号（可选，缺省则跳过并发校验）
    test_item_id: Optional[int] = None
    item_revision: Optional[int] = None


class BomIndicatorBatchUpdateReq(BaseModel):
    ids: List[int]
    unit: Optional[str] = None
    judgment_rule: Optional[str] = None
    test_stage: Optional[str] = None


class BomIndicatorBatchStatusReq(BaseModel):
    ids: List[int]
    status: int


# ── Per-param CRUD (single param within a BOM indicator) ──
class BomIndicatorParamAddReq(BaseModel):
    param_key: str = Field(..., max_length=80)
    param_name: str = ""
    param_value: Any = ""
    param_type: str = "通用测试参数"
    remark: str = ""


class BomIndicatorParamUpdateReq(BaseModel):
    param_name: Optional[str] = None
    param_value: Optional[Any] = None
    param_type: Optional[str] = None
    remark: Optional[str] = None
    # 乐观锁：所属测试项 id 与客户端持有的版本号（可选，缺省则跳过并发校验）
    test_item_id: Optional[int] = None
    item_revision: Optional[int] = None


class IndicatorParamAddReq(BaseModel):
    param_key: str = Field(..., max_length=80)
    param_name: str = ""
    param_value: Any = ""
    param_type: str = "通用测试参数"
    remark: str = ""


class IndicatorParamUpdateReq(BaseModel):
    param_name: Optional[str] = None
    param_value: Optional[Any] = None
    param_type: Optional[str] = None
    remark: Optional[str] = None


class BomIndicatorResp(BaseModel):
    id: int
    bom_config_id: int
    indicator_id: int
    indicator_code: str
    indicator_name: str
    category: str
    unit: str
    judgment_rule: str
    test_stage: str
    remark: str
    status: int
    params: list = []
    dict_params: dict = {}
    item_revision: int = 0
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None


# ── Copy ──
class BomConfigCopyReq(BaseModel):
    target_bom_code: str = Field(..., max_length=100)
    target_bom_name: str = ""


# ── Domain Owners (领域 → 负责人映射) ──
class BomDomainOwnersReq(BaseModel):
    domain_owners: dict = {}


class BomDomainOwnersResp(BaseModel):
    domain_owners: dict = {}
    domains: list = []


# ── Version Snapshot ──
class VersionSnapshotResp(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    version: int
    snapshot_data: dict
    change_summary: str
    operator: str
    created_at: Optional[str] = None


# ── Query ──
class IndicatorQueryReq(BaseModel):
    bom_code: str = ""
    collection_id: Optional[int] = None
    indicator_name: str = ""
    product_type: str = ""


class IndicatorQueryResp(BaseModel):
    bom_config_id: int
    bom_code: str
    bom_name: str
    collection_id: int
    collection_name: str
    test_item_id: Optional[int] = None
    test_item_name: Optional[str] = None
    indicator_id: int
    indicator_code: str
    indicator_name: str
    category: str
    unit: str
    judgment_rule: str
    test_stage: str


# ── Test Item Indicator ──
class TestItemIndicatorCreateReq(BaseModel):
    indicator_id: int
    unit: str = ""
    judgment_rule: str = "合格"


class TestItemIndicatorBatchCreateReq(BaseModel):
    indicators: List[TestItemIndicatorCreateReq]


class TestItemIndicatorResp(BaseModel):
    id: int
    test_item_id: int
    indicator_id: int
    unit: str
    judgment_rule: str
    indicator_code: str = ""
    indicator_name: str = ""
    category: str = ""
    dict_status: int = 1
    test_params: List[dict] = []


class IndicatorBatchItem(BaseModel):
    id: int
    unit: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None


class IndicatorBatchUpdateReq(BaseModel):
    items: List[IndicatorBatchItem]


# ── Script Template ──
class ScriptTemplateCreateReq(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = ""
    source_code: str = Field(..., description="Python 脚本源码")
    output_format: str = Field(default="json", pattern="^(json|ini)$")


class ScriptTemplateUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_code: Optional[str] = None
    output_format: Optional[str] = None
    status: Optional[int] = None


class ScriptTemplateResp(BaseModel):
    id: int
    name: str
    description: str
    source_code: str
    output_format: str
    status: int
    created_by: str
    updated_by: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ScriptExecuteReq(BaseModel):
    script_id: int
    indicator_ids: List[int] = Field(default=[], description="指标字典 ID 列表")
    collection_ids: List[int] = Field(default=[], description="测试项集合 ID 列表")
    bom_config_ids: List[int] = Field(default=[], description="BOM 配置 ID 列表")
    export_all: bool = False


class ScriptExecuteResp(BaseModel):
    file_id: int
    file_name: str
    file_size: int
    download_url: str
    execution_time_ms: int


# ── Indicator Reference ──
class IndicatorReferenceResp(BaseModel):
    indicator_id: int
    indicator_code: str
    indicator_name: str
    collections: List[dict] = []
    bom_configs: List[dict] = []


# ── Script Validate ──
class ScriptValidateReq(BaseModel):
    source_code: str


# ── BOM Export ──
class BomExportReq(BaseModel):
    output_format: str = Field(default="json", pattern="^(json|ini)$")


class BomExportItem(BaseModel):
    indicator_code: str
    indicator_name: str
    script_name: str
    status: str
    execution_time_ms: int
    error: str = ""


class BomExportResp(BaseModel):
    file_id: str
    file_name: str
    file_size: int
    download_url: str
    execution_time_ms: int
    total_indicators: int
    succeeded: int
    failed: int
    logs: List[BomExportItem] = []


# ── Review / Archive ──
class ReviewReq(BaseModel):
    comment: str = ""
    change_summary: str = Field(..., min_length=1, description="版本变更备注（必填）")

class ReviewActionResp(BaseModel):
    id: int
    review_status: str
    review_comment: Optional[str] = None
    review_operator: Optional[str] = None
    reviewed_at: Optional[str] = None


# ── Collaborative Editing ──
class IndicatorParamSaveItem(BaseModel):
    indicator_id: int
    param_key: str
    param_value: str
    item_revision: int
    test_item_id: Optional[int] = 0
    test_item_name: Optional[str] = ""


class BomIndicatorBatchSaveReq(BaseModel):
    indicators: List[IndicatorParamSaveItem]


class BomIndicatorBatchSaveResp(BaseModel):
    success: List[int]
    conflicts: List[dict]


class ParamChangeLogResp(BaseModel):
    id: int
    bom_code: str
    bom_config_id: int
    bom_version: int
    test_item_id: int
    test_item_name: str
    indicator_id: int
    indicator_code: str
    indicator_name: str
    param_key: str
    param_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    operator_id: Optional[int] = None
    operator_name: str
    created_at: str


# WebSocket Online Users
class OnlineUserInfo(BaseModel):
    user_id: int
    user_name: str
    connected_at: str
    archived: bool = False
    archived_at: Optional[str] = None


# ── Rollback ──
class RollbackReq(BaseModel):
    operator: str = ""
