from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class VersionCreateReq(BaseModel):
    project_name: str = ""
    version: str
    description: str = ""
    type: str = "standard"
    sequence_id: int = 0
    process_type: str = ""
    workstation: str = ""
    codes_config: list = []
    bom_code: str = ""
    tps_name: str = ""
    domain_tags: str = ""
    inherit_from_id: Optional[int] = None
    archive_items: list = []
    sub_scenarios: list = []
    steps_config: dict = {}


class VersionUpdateReq(BaseModel):
    description: Optional[str] = None
    sequence_id: Optional[int] = None
    process_type: Optional[str] = None
    workstation: Optional[str] = None
    codes_config: Optional[list] = None
    bom_code: Optional[str] = None
    tps_name: Optional[str] = None
    domain_tags: Optional[str] = None
    sub_scenarios: Optional[list] = None
    archive_items: Optional[list] = None
    steps_config: Optional[dict] = None


class VersionResp(BaseModel):
    id: int
    version: str
    project_name: str
    description: str
    status: str
    created_by: str
    sequence_id: int
    process_type: str
    workstation: str
    codes_config: list
    type: str
    bom_code: str
    tps_name: str
    domain_tags: str
    inherit_from_id: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SubScenarioCreateReq(BaseModel):
    name: str
    description: str = ""
    sort_order: int = 0
    process_type: str = ""
    workstation: str = ""
    sequence_id: int = 0
    hardware_params: Any = {}
    software_metrics: list = []
    property_page: Any = {}
    metrics_json: str = ""
    metrics_ini: str = ""


class SubScenarioUpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    process_type: Optional[str] = None
    workstation: Optional[str] = None
    sequence_id: Optional[int] = None
    hardware_params: Optional[Any] = None
    software_metrics: Optional[list] = None
    property_page: Optional[Any] = None
    metrics_json: Optional[str] = None
    metrics_ini: Optional[str] = None


class SubScenarioResp(BaseModel):
    id: int
    version_id: int
    name: str
    description: str
    sort_order: int
    process_type: str
    workstation: str
    sequence_id: int
    hardware_params: Any
    software_metrics: list
    property_page: Any
    metrics_json: str = ""
    metrics_ini: str = ""
    created_at: Optional[datetime]


class StepSubmitReq(BaseModel):
    step_id: int
    action: str = "approve"
    comment: str = ""


class AssignApproversReq(BaseModel):
    test_manager: str = ""
    project_manager: str = ""


class TargetItem(BaseModel):
    factory_id: Optional[int] = None
    factory_name: str = ""
    line_id: Optional[int] = None
    line_name: str = ""
    station_id: Optional[int] = None
    station_name: str = ""
    assign_te: bool = False


class DeploymentCreateReq(BaseModel):
    targets: List[TargetItem] = []
    te_engineer: str = ""


class DeploymentApproveReq(BaseModel):
    action: str = "approve"
    comment: str = ""


class DeploymentResp(BaseModel):
    id: int
    version_id: int
    factory_id: Optional[int]
    factory_name: str
    line_id: Optional[int]
    line_name: str
    station_id: Optional[int]
    station_name: str
    assigned_to: str
    status: str
    approved_by: str
    approved_at: Optional[datetime]
    comment: str
    deployed_at: Optional[datetime]
    created_at: Optional[datetime]


class ArchiveItemResp(BaseModel):
    id: int
    version_id: int
    type: str
    item_id: Optional[int]
    data_snapshot: Any


class BinaryFileResp(BaseModel):
    id: int
    version_id: int
    sub_scenario_id: Optional[int] = None
    filename: str
    file_size: int
    description: str
    created_at: Optional[datetime] = None


class VersionDetailResp(BaseModel):
    version: VersionResp
    steps: list = []
    sub_scenarios: list = []
    archive_items: list = []
    binary_files: list = []
    deployments: list = []
