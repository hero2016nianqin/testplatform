"""
测试日志保存服务 — 将测试结果保存到装备本地硬盘
路径结构: {base_dir}/{station_id}/success|fail/{serial_number}_{datetime}.log
"""
import os
from datetime import datetime


def save_run_log(
    base_dir: str,
    station_id: int,
    serial_number: str,
    batch_id: str,
    status: str,
    total: int,
    passed: int,
    failed: int,
    items: list[dict] | None = None,
    slot_info: str = "",
):
    folder = "success" if status == "completed" else "fail"
    log_dir = os.path.join(base_dir, str(station_id), folder)
    os.makedirs(log_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_sn = (serial_number or "unknown").replace("/", "_").replace("\\", "_")
    filename = f"{safe_sn}_{ts}.log"
    filepath = os.path.join(log_dir, filename)

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  测试报告")
    lines.append(f"{'='*60}")
    lines.append(f"  条码:     {serial_number or '-'}")
    lines.append(f"  批次:     {batch_id}")
    lines.append(f"  槽位:     {slot_info or '-'}")
    lines.append(f"  结果:     {'通过' if status == 'completed' else '失败'}")
    lines.append(f"  时间:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  总计:     {total}")
    lines.append(f"  通过:     {passed}")
    lines.append(f"  失败:     {failed}")
    lines.append(f"{'='*60}")
    lines.append("")

    if items:
        lines.append(f"  {'序号':<6} {'测试项目':<24} {'期望值':<12} {'实际值':<12} {'结果':<6}")
        lines.append(f"  {'-'*60}")
        for i, item in enumerate(items, 1):
            result_mark = "✓" if item.get("passed") else "✗"
            lines.append(
                f"  {i:<6} {item.get('name', '-'):<24} "
                f"{item.get('expected', '-'):<12} "
                f"{item.get('actual', '-'):<12} "
                f"{result_mark:<6}"
            )
        lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
