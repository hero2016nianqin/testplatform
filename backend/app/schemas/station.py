from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ── Factory ──
class FactoryCreateReq(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = None
    description: str = ""
    sort_order: int = 0


class FactoryUpdateReq(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


class FactoryResp(BaseModel):
    id: int
    name: str
    code: Optional[str]
    description: str
    sort_order: int


# ── Line ──
class LineCreateReq(BaseModel):
    factory_id: int
    name: str = Field(..., max_length=100)
    code: Optional[str] = None
    description: str = ""
    scenario: str = ""
    created_by: str = ""
    sort_order: int = 0


class LineUpdateReq(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    scenario: Optional[str] = None
    sort_order: Optional[int] = None


class LineResp(BaseModel):
    id: int
    factory_id: int
    name: str
    code: Optional[str]
    description: str
    scenario: str
    created_by: str
    sort_order: int


# ── EquipmentDefinition ──
class DefinitionCreateReq(BaseModel):
    name: str = Field(..., max_length=100)
    code: Optional[str] = None
    description: str = ""
    layout_config: dict = {}
    default_equipment_config: dict = {}
    default_hardware_params: list = []
    default_software_config: dict = {}
    default_scenario_config: dict = {}


class DefinitionUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    current_version: Optional[str] = None
    layout_config: Optional[dict] = None


class DefinitionResp(BaseModel):
    id: int
    name: str
    code: Optional[str]
    description: str
    current_version: str
    layout_config: dict


# ── Station ──
class StationCreateReq(BaseModel):
    line_id: int
    definition_id: int
    name: str = Field(..., max_length=100)
    code: Optional[str] = None
    description: str = ""
    process_type: str = ""
    workstation: str = ""
    actuator: str = ""
    hardware_code: str = ""
    software_code: str = ""
    created_by: str = ""


class StationUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    process_type: Optional[str] = None
    workstation: Optional[str] = None
    actuator: Optional[str] = None
    hardware_code: Optional[str] = None
    software_code: Optional[str] = None
    has_settings: Optional[bool] = None
    sort_order: Optional[int] = None


class StationResp(BaseModel):
    id: int
    line_id: Optional[int]
    definition_id: Optional[int]
    name: str
    code: Optional[str]
    description: str
    deployed_version: str
    latest_version: str
    needs_update: bool
    process_type: str
    workstation: str
    actuator: str
    hardware_code: str
    software_code: str
    has_settings: bool
    sort_order: int


class SlotResp(BaseModel):
    id: int
    chassis_id: int
    name: str
    status: str
    current_batch_id: Optional[str]
    serial_number: Optional[str] = None
    sort_order: int


class ChassisResp(BaseModel):
    id: int
    station_id: int
    cabinet_id: Optional[int]
    name: str
    slot_count: int
    sort_order: int
    slots: List[SlotResp] = []


class CabinetResp(BaseModel):
    id: int
    station_id: int
    name: str
    sort_order: int
    chassis_list: List[ChassisResp] = []


class CabinetParamResp(BaseModel):
    id: int
    cabinet_id: int
    param_name: str
    param_value: str
    group_name: str
    sort_order: int


class CabinetParamCreateReq(BaseModel):
    param_name: str
    param_value: str = ""
    group_name: str = "default"
    sort_order: int = 0


class CabinetParamUpdateReq(BaseModel):
    param_name: Optional[str] = None
    param_value: Optional[str] = None
    group_name: Optional[str] = None
    sort_order: Optional[int] = None


class ChassisParamResp(BaseModel):
    id: int
    chassis_id: int
    param_name: str
    param_value: str
    group_name: str
    sort_order: int


class ChassisParamCreateReq(BaseModel):
    param_name: str
    param_value: str = ""
    group_name: str = "default"
    sort_order: int = 0


class ChassisParamUpdateReq(BaseModel):
    param_name: Optional[str] = None
    param_value: Optional[str] = None
    group_name: Optional[str] = None
    sort_order: Optional[int] = None


class StationDetailResp(BaseModel):
    station: StationResp
    cabinets: List[CabinetResp] = []
