"""
种子数据脚本
对应 design.md §11 — 4 类默认用户 + 厂区线体装备 + 测试模板序列 + 硬件参数样本
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.station import Factory, ProductionLine, TestStation, Cabinet, TestChassis, TestSlot
from app.models.station_config import EquipmentConfig, HardwareParam, SoftwareConfig, ScenarioConfig
from app.models.equipment import EquipmentDefinition, EquipmentMetrics, EquipmentPropertyPage
from app.models.test_sequence import TestItemTemplate, TestSequence, TestSequenceStep


async def seed():
    async with AsyncSessionLocal() as session:
        existing = await session.get(User, 1)
        if existing:
            print("Seed data already exists, skipping.")
            return

        # ── 4 类用户 ──
        users = [
            User(username="admin", display_name="超级管理员", password_hash=hash_password("admin123"), role="super_admin", registration_status="active"),
            User(username="developer", display_name="装备开发人员", password_hash=hash_password("123456"), role="equipment_developer", registration_status="active"),
            User(username="process", display_name="工艺人员", password_hash=hash_password("123456"), role="process", registration_status="active"),
            User(username="operator", display_name="操作人员", password_hash=hash_password("123456"), role="operator", registration_status="active"),
        ]
        session.add_all(users)
        await session.flush()

        # ── 厂区 ──
        f1 = Factory(name="SMT 一厂", code="SMT-01", sort_order=1)
        f2 = Factory(name="组装厂", code="ASSY-01", sort_order=2)
        session.add_all([f1, f2])
        await session.flush()

        # ── 线体 ──
        lines_data = [
            (f1.id, "SMT 线体 01", "SMT-L01", 1),
            (f1.id, "SMT 线体 02", "SMT-L02", 2),
            (f2.id, "组装线 01", "ASSY-L01", 1),
        ]
        lines = [ProductionLine(factory_id=fid, name=n, code=c, sort_order=s) for fid, n, c, s in lines_data]
        session.add_all(lines)
        await session.flush()

        # ── 装备定义 ──
        defs = [
            EquipmentDefinition(name="SPI 检测装备", code="SPI-001", current_version="2.1.0",
                                layout_config={"cabinets": [{"name": "机柜 1", "chassis": [{"name": "机框 1", "slot_count": 4}, {"name": "机框 2", "slot_count": 4}]}]}),
            EquipmentDefinition(name="贴片机测试站", code="P&P-001", current_version="1.5.0",
                                layout_config={"cabinets": [{"name": "机柜 1", "chassis": [{"name": "机框 1", "slot_count": 4}, {"name": "机框 2", "slot_count": 4}, {"name": "机框 3", "slot_count": 2}]}]}),
            EquipmentDefinition(name="功能测试站", code="FCT-001", current_version="3.0.0",
                                layout_config={"cabinets": [{"name": "机柜 1", "chassis": [{"name": "机框 1", "slot_count": 8}]}]}),
        ]
        session.add_all(defs)
        await session.flush()

        # ── 工站 ──
        stations = [
            TestStation(line_id=lines[0].id, definition_id=defs[0].id, name="SPI-01", code="SPI-01", process_type="SPI", has_settings=True),
            TestStation(line_id=lines[0].id, definition_id=defs[0].id, name="SPI-02", code="SPI-02", process_type="SPI", has_settings=True),
            TestStation(line_id=lines[1].id, definition_id=defs[1].id, name="P&P-01", code="P&P-01", process_type="贴片", has_settings=True),
            TestStation(line_id=lines[2].id, definition_id=defs[2].id, name="FCT-01", code="FCT-01", process_type="FT", has_settings=True),
        ]
        session.add_all(stations)
        await session.flush()

        # ── 机柜/机框/槽位 ──
        for st in stations:
            layout = st.definition.layout_config if st.definition else None
            if not layout:
                continue
            for cab_data in layout.get("cabinets", []):
                cab = Cabinet(station_id=st.id, name=cab_data.get("name", "机柜 1"))
                session.add(cab)
                await session.flush()
                for ch_data in cab_data.get("chassis", []):
                    ch = TestChassis(station_id=st.id, cabinet_id=cab.id, name=ch_data["name"], slot_count=ch_data["slot_count"])
                    session.add(ch)
                    await session.flush()
                    for i in range(ch_data["slot_count"]):
                        slot = TestSlot(chassis_id=ch.id, name=f"槽位 {i+1}", sort_order=i)
                        session.add(slot)

        # ── 装备参数 ──
        for st in stations:
            session.add(EquipmentConfig(station_id=st.id))
            session.add(SoftwareConfig(station_id=st.id))
            session.add(ScenarioConfig(station_id=st.id))
            session.add(EquipmentMetrics(station_id=st.id))
            session.add(EquipmentPropertyPage(station_id=st.id))

            # 硬件参数样本
            hw_samples = [
                ("测试仪 IP", "192.168.1.100", "网络", 1),
                ("测试仪端口", "5025", "网络", 2),
                ("万用表 IP", "192.168.1.101", "测量", 3),
                ("万用表型号", "34461A", "测量", 4),
                ("电源 IP", "192.168.1.102", "电源", 5),
                ("电源通道数", "4", "电源", 6),
                ("GPIB 地址", "10", "接口", 7),
                ("串口波特率", "115200", "接口", 8),
            ]
            for name, val, group, order in hw_samples:
                session.add(HardwareParam(station_id=st.id, param_name=name, param_value=val, group_name=group, sort_order=order))

        await session.flush()

        # ── 测试项模板 (6个) ──
        templates_data = [
            ("电压测试", True, 30, "电气"),
            ("电流测试", False, 30, "电气"),
            ("频率测试", False, 20, "射频"),
            ("温度测量", True, 60, "环境"),
            ("绝缘测试", True, 60, "安全"),
            ("噪声测试", False, 30, "声学"),
        ]
        templates = []
        for name, critical, timeout, cat in templates_data:
            t = TestItemTemplate(name=name, is_critical=critical, timeout_seconds=timeout, category=cat)
            session.add(t)
            templates.append(t)
        await session.flush()

        # ── 测试序列 (1个) ──
        seq = TestSequence(name="FCT 标准测试序列", version="1.0", created_by="admin")
        session.add(seq)
        await session.flush()

        for i, t in enumerate(templates):
            session.add(TestSequenceStep(sequence_id=seq.id, template_id=t.id, step_order=i + 1, timeout_seconds=t.timeout_seconds))

        await session.commit()
        print("Seed data created successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
