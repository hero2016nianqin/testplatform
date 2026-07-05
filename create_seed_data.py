import sys
import os
sys.path.insert(0, '.')

from app import create_app, db
from app.models.station import Factory, ProductionLine, EquipmentDefinition, TestStation, HardwareParam, TestChassis, TestSlot, Cabinet
from app.models.test_sequence import TestSequence, TestSequenceStep, TestItemTemplate

app = create_app()

with app.app_context():
    print("=== Creating sample data ===\n")
    
    # Create factories
    f1 = Factory(name='SMT 一厂', code='SMT01', description='SMT 表面贴装工厂', sort_order=1)
    f2 = Factory(name='组装厂', code='ASM01', description='整机组装工厂', sort_order=2)
    db.session.add_all([f1, f2])
    db.session.flush()
    print(f"Created factories: {Factory.query.count()}")
    
    # Create lines
    l1 = ProductionLine(factory_id=f1.id, name='SMT 线体 01', code='SMT-L01', description='高速贴片线', sort_order=1)
    l2 = ProductionLine(factory_id=f1.id, name='SMT 线体 02', code='SMT-L02', description='多功能贴片线', sort_order=2)
    l3 = ProductionLine(factory_id=f2.id, name='组装线 01', code='ASM-L01', description='主线组装', sort_order=1)
    db.session.add_all([l1, l2, l3])
    db.session.flush()
    print(f"Created lines: {ProductionLine.query.count()}")
    
    # Create equipment definitions
    def1 = EquipmentDefinition(name='SPI 检测装备', code='SPI-01', description='锡膏检测仪', current_version='2.1.0',
                              layout_config={
        "cabinets": [{"name": "机柜 1", "chassis": [
            {"name": "机框 1", "slot_count": 4},
            {"name": "机框 2", "slot_count": 4}]}]})
    def2 = EquipmentDefinition(name='贴片机测试站', code='SMT-T01', description='贴片后电气测试',
                              current_version='1.5.0', layout_config={
        "cabinets": [{"name": "机柜 1", "chassis": [
            {"name": "机框 1", "slot_count": 4},
            {"name": "机框 2", "slot_count": 4},
            {"name": "机框 3", "slot_count": 2}]}]})
    def3 = EquipmentDefinition(name='功能测试站', code='FCT-01', description='整机功能测试',
                              current_version='3.0.0', layout_config={
        "cabinets": [{"name": "机柜 1", "chassis": [
            {"name": "机框 1", "slot_count": 8}]}]})
    db.session.add_all([def1, def2, def3])
    db.session.flush()
    print(f"Created equipment definitions: {EquipmentDefinition.query.count()}")
    
    # Create test stations (actual equipment instances)
    s1 = TestStation(line_id=l1.id, name='SPI 检测装备', code='SPI-01', description='锡膏检测仪', sort_order=1,
                    deployed_version='2.0.0', latest_version=def1.current_version,
                    definition_id=def1.id, hardware_code='SPI-01-001', software_code='SW-01-001')
    s2 = TestStation(line_id=l1.id, name='贴片机测试站', code='SMT-T01', description='贴片后电气测试', sort_order=2,
                    deployed_version=def2.current_version, latest_version=def2.current_version,
                    definition_id=def2.id, hardware_code='SMT-T01-002', software_code='SW-01-002')
    s3 = TestStation(line_id=l3.id, name='功能测试站', code='FCT-01', description='整机功能测试', sort_order=1,
                    deployed_version='2.5.0', latest_version=def3.current_version,
                    definition_id=def3.id, hardware_code='FCT-01-003', software_code='SW-02-001')
    db.session.add_all([s1, s2, s3])
    db.session.flush()
    print(f"Created test stations (equipment): {TestStation.query.count()}")
    print(f"  - Station ID: {s1.id}, Name: {s1.name}, Hardware Code: {s1.hardware_code}")
    print(f"  - Station ID: {s2.id}, Name: {s2.name}, Hardware Code: {s2.hardware_code}")
    print(f"  - Station ID: {s3.id}, Name: {s3.name}, Hardware Code: {s3.hardware_code}")
    
    # Create basic hardware params for stations
    hw1 = HardwareParam(station_id=s1.id, param_name='测试仪 IP', param_value='192.168.1.100',
                       group_name='网络配置', sort_order=1)
    hw2 = HardwareParam(station_id=s1.id, param_name='测试仪端口', param_value='5025',
                       group_name='网络配置', sort_order=2)
    db.session.add_all([hw1, hw2])
    
    # Station 2 hardware params
    hw3 = HardwareParam(station_id=s2.id, param_name='万用表 IP', param_value='192.168.1.101',
                       group_name='仪器配置', sort_order=1)
    db.session.add(hw3)
    
    # Station 3 hardware params
    hw4 = HardwareParam(station_id=s3.id, param_name='电源 IP', param_value='192.168.1.102',
                       group_name='仪器配置', sort_order=1)
    hw5 = HardwareParam(station_id=s3.id, param_name='电源通道数', param_value='2',
                       group_name='仪器配置', sort_order=2)
    db.session.add_all([hw4, hw5])
    
    db.session.flush()
    print(f"Created hardware params: {HardwareParam.query.count()}")
    
    # Create basic test sequence and templates
    tpl1 = TestItemTemplate(name='电压测试', service_address='http://service-test:5001/test/voltage',
                           is_critical=True, timeout_seconds=30, category='电气', sort_order=0)
    tpl2 = TestItemTemplate(name='电流测试', service_address='http://service-test:5001/test/current',
                           is_critical=False, timeout_seconds=30, category='电气', sort_order=1)
    tpl3 = TestItemTemplate(name='频率测试', service_address='http://service-test:5001/test/frequency',
                           is_critical=False, timeout_seconds=60, category='射频', sort_order=2)
    db.session.add_all([tpl1, tpl2, tpl3])
    db.session.flush()
    print(f"Created test item templates: {TestItemTemplate.query.count()}")
    
    seq = TestSequence(name='FCT 标准测试序列', description='功能测试标准流程', version='1.0')
    db.session.add(seq)
    db.session.flush()
    print(f"Created test sequence: {seq.id}, name: {seq.name}")
    
    for t in [tpl1, tpl2, tpl3]:
        db.session.add(TestSequenceStep(sequence_id=seq.id, template_id=t.id, step_order=t.sort_order, timeout_seconds=t.timeout_seconds))
    db.session.flush()
    print(f"Created sequence steps: {TestSequenceStep.query.count()}")
    
    db.session.commit()
    
    print("\n=== System Data Summary ===")
    print(f"Factories: {Factory.query.count()}")
    print(f"Lines: {ProductionLine.query.count()}")
    print(f"Equipment Definitions: {EquipmentDefinition.query.count()}")
    print(f"Test Stations (Equipment): {TestStation.query.count()}")
    print(f"Test Item Templates: {TestItemTemplate.query.count()}")
    print(f"Test Sequences: {TestSequence.query.count()}")
    print(f"Test Sequence Steps: {TestSequenceStep.query.count()}")
    print(f"Hardware Params: {HardwareParam.query.count()}")
    
