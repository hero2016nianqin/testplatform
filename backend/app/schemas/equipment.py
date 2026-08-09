from typing import Optional, Any, List
from pydantic import BaseModel, Field


class EquipmentConfigReq(BaseModel):
    auto_load_enabled: Optional[bool] = None
    debug_mode_enabled: Optional[bool] = None
    equipment_ip: Optional[str] = None
    equipment_service_address: Optional[str] = None
    process_control_enabled: Optional[bool] = None
    test_mode_normal: Optional[bool] = None
    test_mode_verify: Optional[bool] = None
    test_mode_calibration: Optional[bool] = None
    barcode_verify_enabled: Optional[bool] = None


class EquipmentConfigResp(BaseModel):
    id: int
    station_id: int
    auto_load_enabled: bool
    debug_mode_enabled: bool
    equipment_ip: str
    equipment_service_address: str
    process_control_enabled: bool
    test_mode_normal: bool
    test_mode_verify: bool
    test_mode_calibration: bool
    barcode_verify_enabled: bool


class HardwareParamCreateReq(BaseModel):
    param_name: str
    param_value: str = ""
    group_name: str = "default"
    sort_order: int = 0


class HardwareParamUpdateReq(BaseModel):
    param_name: Optional[str] = None
    param_value: Optional[str] = None
    group_name: Optional[str] = None
    sort_order: Optional[int] = None


class HardwareParamResp(BaseModel):
    id: int
    station_id: int
    param_name: str
    param_value: str
    group_name: str
    sort_order: int


class HardwareBatchReplaceReq(BaseModel):
    params: List[HardwareParamCreateReq]


class SoftwareConfigReq(BaseModel):
    project_name: Optional[str] = None
    dut_version: Optional[str] = None
    dut_firmware_version: Optional[str] = None
    dut_hardware_version: Optional[str] = None
    selected_test_item_ids: Optional[List[int]] = None
    sequence_id: Optional[int] = None
    sequence_data: Optional[Any] = None
    process_type: Optional[str] = None
    workstation: Optional[str] = None
    selected_code: Optional[str] = None
    bom_code: Optional[str] = None


class SoftwareConfigResp(BaseModel):
    id: int
    station_id: int
    project_name: str
    dut_version: str
    dut_firmware_version: str
    dut_hardware_version: str
    selected_test_item_ids: list
    sequence_id: int
    sequence_data: Any
    process_type: str
    workstation: str
    selected_code: str
    bom_code: str


class ScenarioConfigReq(BaseModel):
    scenario_data: Any


class ScenarioConfigResp(BaseModel):
    id: int
    station_id: int
    scenario_data: Any


class MetricsReq(BaseModel):
    metrics: list


class MetricsResp(BaseModel):
    id: int
    station_id: int
    metrics: list


class PropertyPageReq(BaseModel):
    page_data: dict


class PropertyPageResp(BaseModel):
    id: int
    station_id: int
    page_data: dict


class SyncVersionPropsReq(BaseModel):
    version_id: int


# ── Chassis & Slot ──
class ChassisCreateReq(BaseModel):
    name: str = "新机框"
    slot_count: int = 1


class ChassisUpdateReq(BaseModel):
    name: Optional[str] = None
    slot_count: Optional[int] = None
    sort_order: Optional[int] = None


class SlotUpdateReq(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    current_batch_id: Optional[str] = None
    sort_order: Optional[int] = None
