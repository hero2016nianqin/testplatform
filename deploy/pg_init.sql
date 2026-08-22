-- Test Platform — PostgreSQL initialization
-- Creates partitioned tables for high-volume data

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL DEFAULT '',
    role INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Stations hierarchy
CREATE TABLE IF NOT EXISTS factories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE,
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS production_lines (
    id SERIAL PRIMARY KEY,
    factory_id INTEGER NOT NULL REFERENCES factories(id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50),
    description TEXT DEFAULT '',
    scenario VARCHAR(100) DEFAULT '',
    created_by VARCHAR(100) DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS equipment_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(50) UNIQUE,
    description TEXT DEFAULT '',
    current_version VARCHAR(20) DEFAULT '1.0.0',
    layout_config JSONB DEFAULT '{}',
    default_equipment_config JSONB DEFAULT '{}',
    default_hardware_params JSONB DEFAULT '[]',
    default_software_config JSONB DEFAULT '{}',
    default_scenario_config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_stations (
    id SERIAL PRIMARY KEY,
    line_id INTEGER REFERENCES production_lines(id),
    definition_id INTEGER REFERENCES equipment_definitions(id),
    name VARCHAR(100) UNIQUE NOT NULL,
    code VARCHAR(50),
    description TEXT DEFAULT '',
    deployed_version VARCHAR(20) DEFAULT '1.0.0',
    latest_version VARCHAR(20) DEFAULT '1.0.0',
    process_type VARCHAR(50) DEFAULT '',
    workstation VARCHAR(50) DEFAULT '',
    actuator VARCHAR(100) DEFAULT '',
    hardware_code VARCHAR(100) DEFAULT '',
    software_code VARCHAR(100) DEFAULT '',
    created_by VARCHAR(100) DEFAULT '',
    has_settings BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cabinets (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES test_stations(id),
    name VARCHAR(100) NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_chassis (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES test_stations(id),
    cabinet_id INTEGER REFERENCES cabinets(id),
    name VARCHAR(100) NOT NULL,
    slot_count INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_slots (
    id SERIAL PRIMARY KEY,
    chassis_id INTEGER NOT NULL REFERENCES test_chassis(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'idle',
    current_batch_id VARCHAR(50),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cabinet params
CREATE TABLE IF NOT EXISTS cabinet_params (
    id SERIAL PRIMARY KEY,
    cabinet_id INTEGER NOT NULL REFERENCES cabinets(id),
    param_name VARCHAR(200) NOT NULL,
    param_value VARCHAR(500) DEFAULT '',
    group_name VARCHAR(100) DEFAULT 'default',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cabinet_params_cabinet ON cabinet_params (cabinet_id);

-- Chassis params
CREATE TABLE IF NOT EXISTS chassis_params (
    id SERIAL PRIMARY KEY,
    chassis_id INTEGER NOT NULL REFERENCES test_chassis(id),
    param_name VARCHAR(200) NOT NULL,
    param_value VARCHAR(500) DEFAULT '',
    group_name VARCHAR(100) DEFAULT 'default',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_chassis_params_chassis ON chassis_params (chassis_id);

-- Station configs
CREATE TABLE IF NOT EXISTS equipment_configs (
    id SERIAL PRIMARY KEY,
    station_id INTEGER UNIQUE NOT NULL REFERENCES test_stations(id),
    auto_load_enabled BOOLEAN DEFAULT FALSE,
    debug_mode_enabled BOOLEAN DEFAULT FALSE,
    equipment_ip VARCHAR(50) DEFAULT '192.168.1.100',
    equipment_service_address VARCHAR(200) DEFAULT '',
    process_control_enabled BOOLEAN DEFAULT TRUE,
    test_mode_normal BOOLEAN DEFAULT TRUE,
    test_mode_verify BOOLEAN DEFAULT FALSE,
    test_mode_calibration BOOLEAN DEFAULT FALSE,
    barcode_verify_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hardware_params (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES test_stations(id),
    param_name VARCHAR(200) NOT NULL,
    param_value VARCHAR(500) DEFAULT '',
    group_name VARCHAR(100) DEFAULT 'default',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS software_configs (
    id SERIAL PRIMARY KEY,
    station_id INTEGER NOT NULL REFERENCES test_stations(id),
    project_name VARCHAR(200) DEFAULT '',
    dut_version VARCHAR(100) DEFAULT '',
    dut_firmware_version VARCHAR(100) DEFAULT '',
    dut_hardware_version VARCHAR(100) DEFAULT '',
    selected_test_item_ids JSONB DEFAULT '[]',
    sequence_id INTEGER DEFAULT 0,
    sequence_data JSONB DEFAULT '{}',
    process_type VARCHAR(50) DEFAULT '',
    workstation VARCHAR(50) DEFAULT '',
    selected_code VARCHAR(100) DEFAULT '',
    bom_code VARCHAR(200) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scenario_configs (
    id SERIAL PRIMARY KEY,
    station_id INTEGER UNIQUE NOT NULL REFERENCES test_stations(id),
    scenario_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS equipment_metrics (
    id SERIAL PRIMARY KEY,
    station_id INTEGER UNIQUE NOT NULL REFERENCES test_stations(id),
    metrics JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS equipment_property_pages (
    id SERIAL PRIMARY KEY,
    station_id INTEGER UNIQUE NOT NULL REFERENCES test_stations(id),
    page_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Test items
CREATE TABLE IF NOT EXISTS test_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    expected_value FLOAT DEFAULT 0,
    min_value FLOAT DEFAULT 0,
    max_value FLOAT DEFAULT 0,
    unit VARCHAR(50) DEFAULT '',
    category VARCHAR(50) DEFAULT 'general',
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_item_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    service_address VARCHAR(200) DEFAULT '',
    is_critical BOOLEAN DEFAULT FALSE,
    timeout_seconds INTEGER DEFAULT 60,
    category VARCHAR(50) DEFAULT 'general',
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_sequences (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    version VARCHAR(20) DEFAULT '1.0',
    is_active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(100) DEFAULT '',
    step_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_sequence_steps (
    id SERIAL PRIMARY KEY,
    sequence_id INTEGER NOT NULL REFERENCES test_sequences(id),
    step_order INTEGER NOT NULL,
    timeout_seconds INTEGER DEFAULT 60,
    template_id INTEGER NOT NULL REFERENCES test_item_templates(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Partitioned tables: test_runs, test_results, test_logs
CREATE TABLE IF NOT EXISTS test_runs (
    id SERIAL,
    batch_id VARCHAR(50) NOT NULL,
    product_type VARCHAR(100) DEFAULT '',
    task_order VARCHAR(100) DEFAULT '',
    serial_number VARCHAR(200) DEFAULT '',
    operator VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    total_items INTEGER DEFAULT 0,
    passed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    station_id INTEGER REFERENCES test_stations(id),
    slot_id INTEGER REFERENCES test_slots(id),
    sequence_id INTEGER DEFAULT 0,
    sequence_name VARCHAR(200) DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL,
    test_item_id INTEGER NOT NULL REFERENCES test_items(id),
    test_run_id INTEGER NOT NULL,
    operator VARCHAR(100) NOT NULL,
    serial_number VARCHAR(200) DEFAULT '',
    actual_value FLOAT NOT NULL,
    passed BOOLEAN NOT NULL,
    deviation FLOAT DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    remark TEXT DEFAULT '',
    tested_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, tested_at)
) PARTITION BY RANGE (tested_at);

CREATE TABLE IF NOT EXISTS test_logs (
    id SERIAL,
    run_id INTEGER,
    slot_id INTEGER,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2027-01-01';
    partition_date DATE;
    partition_name TEXT;
BEGIN
    partition_date := start_date;
    WHILE partition_date < end_date LOOP
        partition_name := 'test_runs_' || to_char(partition_date, 'YYYYMM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF test_runs FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_date, partition_date + INTERVAL '1 month');

        partition_name := 'test_results_' || to_char(partition_date, 'YYYYMM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF test_results FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_date, partition_date + INTERVAL '1 month');

        partition_name := 'test_logs_' || to_char(partition_date, 'YYYYMM');
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF test_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name, partition_date, partition_date + INTERVAL '1 month');

        partition_date := partition_date + INTERVAL '1 month';
    END LOOP;
END $$;

-- Version management
CREATE TABLE IF NOT EXISTS test_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    project_name VARCHAR(200) NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'draft',
    created_by VARCHAR(100) DEFAULT '',
    type VARCHAR(50) DEFAULT 'standard',
    sequence_id INTEGER DEFAULT 0,
    process_type VARCHAR(50) DEFAULT '',
    workstation VARCHAR(50) DEFAULT '',
    codes_config JSONB DEFAULT '[]',
    bom_code VARCHAR(200) DEFAULT '',
    tps_name VARCHAR(200) DEFAULT '',
    domain_tags VARCHAR(500) DEFAULT '',
    inherit_from_id INTEGER REFERENCES test_versions(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS release_steps (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES test_versions(id),
    step_name VARCHAR(200) NOT NULL,
    step_order INTEGER NOT NULL DEFAULT 0,
    approver VARCHAR(100) NOT NULL DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    comment TEXT DEFAULT '',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS version_archive_items (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES test_versions(id),
    type VARCHAR(50) NOT NULL,
    item_id INTEGER,
    data_snapshot JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS version_binary_files (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES test_versions(id),
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER DEFAULT 0,
    file_path VARCHAR(500) NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sub_scenarios (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES test_versions(id),
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    process_type VARCHAR(50) DEFAULT '',
    workstation VARCHAR(50) DEFAULT '',
    sequence_id INTEGER DEFAULT 0,
    hardware_params JSONB DEFAULT '{}',
    software_metrics JSONB DEFAULT '[]',
    property_page JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS release_deployments (
    id SERIAL PRIMARY KEY,
    version_id INTEGER NOT NULL REFERENCES test_versions(id),
    factory_id INTEGER REFERENCES factories(id),
    factory_name VARCHAR(100) DEFAULT '',
    line_id INTEGER REFERENCES production_lines(id),
    line_name VARCHAR(100) DEFAULT '',
    station_id INTEGER REFERENCES test_stations(id),
    station_name VARCHAR(100) DEFAULT '',
    assigned_to VARCHAR(100) NOT NULL DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending',
    approved_by VARCHAR(100) DEFAULT '',
    approved_at TIMESTAMP,
    comment TEXT DEFAULT '',
    deployed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for high-volume queries
CREATE INDEX IF NOT EXISTS idx_test_runs_batch_id ON test_runs (batch_id);
CREATE INDEX IF NOT EXISTS idx_test_runs_operator ON test_runs (operator);
CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs (status);
CREATE INDEX IF NOT EXISTS idx_test_runs_serial ON test_runs (serial_number);
CREATE INDEX IF NOT EXISTS idx_test_runs_station_id ON test_runs (station_id);
CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results (test_run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_tested_at ON test_results (tested_at);
CREATE INDEX IF NOT EXISTS idx_test_logs_level ON test_logs (level);
CREATE INDEX IF NOT EXISTS idx_test_logs_created_at ON test_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_hardware_params_station ON hardware_params (station_id);
CREATE INDEX IF NOT EXISTS idx_test_slots_chassis ON test_slots (chassis_id);
CREATE INDEX IF NOT EXISTS idx_release_steps_version ON release_steps (version_id);
CREATE INDEX IF NOT EXISTS idx_sub_scenarios_version ON sub_scenarios (version_id);
