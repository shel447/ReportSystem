from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, List

from ...shared.kernel.paths import telecom_demo_db_path


DEMO_DB_PATH = os.fspath(telecom_demo_db_path())

TABLE_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "dim_region",
        "description": "区域维表，描述省区与城市分层。",
        "columns": [
            ("region_id", "TEXT", "区域主键"),
            ("region_name", "TEXT", "区域名称"),
            ("province", "TEXT", "省份"),
            ("city_tier", "TEXT", "城市等级"),
            ("manager_name", "TEXT", "区域负责人"),
        ],
    },
    {
        "name": "dim_site",
        "description": "站点维表，挂在区域下。",
        "columns": [
            ("site_id", "TEXT", "站点主键"),
            ("region_id", "TEXT", "所属区域"),
            ("site_code", "TEXT", "站点编码"),
            ("site_name", "TEXT", "站点名称"),
            ("site_type", "TEXT", "站点类型"),
            ("maintenance_vendor", "TEXT", "维护厂商"),
            ("build_date", "TEXT", "建站日期"),
            ("latitude", "REAL", "纬度"),
            ("longitude", "REAL", "经度"),
        ],
    },
    {
        "name": "dim_cell",
        "description": "小区维表，挂在站点下。",
        "columns": [
            ("cell_id", "TEXT", "小区主键"),
            ("site_id", "TEXT", "所属站点"),
            ("cell_name", "TEXT", "小区名称"),
            ("technology", "TEXT", "制式"),
            ("band", "TEXT", "频段"),
            ("carrier", "TEXT", "载波"),
            ("azimuth", "INTEGER", "方位角"),
            ("status", "TEXT", "运行状态"),
        ],
    },
    {
        "name": "dim_device",
        "description": "设备维表，设备可挂站点或小区。",
        "columns": [
            ("device_id", "TEXT", "设备主键"),
            ("site_id", "TEXT", "所属站点"),
            ("cell_id", "TEXT", "所属小区"),
            ("device_name", "TEXT", "设备名称"),
            ("device_type", "TEXT", "设备类型"),
            ("vendor", "TEXT", "厂商"),
            ("model", "TEXT", "型号"),
            ("install_date", "TEXT", "安装日期"),
            ("status", "TEXT", "设备状态"),
        ],
    },
    {
        "name": "fact_asset_inventory",
        "description": "资产库存事实表，记录设备及资产状态。",
        "columns": [
            ("asset_id", "TEXT", "资产主键"),
            ("device_id", "TEXT", "设备 ID"),
            ("site_id", "TEXT", "站点 ID"),
            ("asset_category", "TEXT", "资产类别"),
            ("asset_value", "REAL", "资产原值"),
            ("purchase_date", "TEXT", "采购日期"),
            ("warranty_expiry", "TEXT", "保修到期"),
            ("lifecycle_status", "TEXT", "生命周期状态"),
        ],
    },
    {
        "name": "fact_alarm_event",
        "description": "告警事实表，记录设备与站点告警。",
        "columns": [
            ("alarm_id", "TEXT", "告警主键"),
            ("site_id", "TEXT", "站点 ID"),
            ("cell_id", "TEXT", "小区 ID"),
            ("device_id", "TEXT", "设备 ID"),
            ("alarm_date", "TEXT", "告警日期"),
            ("first_occurred_at", "TEXT", "首次发生时间"),
            ("alarm_severity", "TEXT", "告警级别"),
            ("alarm_type", "TEXT", "告警类型"),
            ("cleared", "INTEGER", "是否清除"),
            ("duration_minutes", "INTEGER", "持续时长"),
        ],
    },
    {
        "name": "fact_cell_kpi_daily",
        "description": "小区日级 KPI 事实表。",
        "columns": [
            ("kpi_id", "TEXT", "KPI 主键"),
            ("cell_id", "TEXT", "小区 ID"),
            ("stat_date", "TEXT", "统计日期"),
            ("prb_utilization", "REAL", "PRB 利用率"),
            ("downlink_traffic_gb", "REAL", "下行流量 GB"),
            ("uplink_traffic_gb", "REAL", "上行流量 GB"),
            ("accessibility_rate", "REAL", "接通率"),
            ("retainability_rate", "REAL", "保持率"),
            ("drop_call_rate", "REAL", "掉话率"),
        ],
    },
    {
        "name": "fact_traffic_hourly",
        "description": "站点/小区小时级流量表。",
        "columns": [
            ("traffic_id", "TEXT", "流量主键"),
            ("site_id", "TEXT", "站点 ID"),
            ("cell_id", "TEXT", "小区 ID"),
            ("stat_hour", "TEXT", "统计小时"),
            ("traffic_gb", "REAL", "流量 GB"),
            ("peak_users", "INTEGER", "峰值用户数"),
            ("packet_loss_rate", "REAL", "丢包率"),
            ("latency_ms", "REAL", "时延 ms"),
        ],
    },
    {
        "name": "fact_work_order",
        "description": "工单事实表，记录维护闭环情况。",
        "columns": [
            ("work_order_id", "TEXT", "工单主键"),
            ("site_id", "TEXT", "站点 ID"),
            ("cell_id", "TEXT", "小区 ID"),
            ("device_id", "TEXT", "设备 ID"),
            ("created_date", "TEXT", "创建日期"),
            ("closed_date", "TEXT", "关闭日期"),
            ("order_type", "TEXT", "工单类型"),
            ("priority", "TEXT", "优先级"),
            ("status", "TEXT", "工单状态"),
            ("sla_breached", "INTEGER", "是否超 SLA"),
        ],
    },
    {
        "name": "fact_site_inspection",
        "description": "站点巡检事实表。",
        "columns": [
            ("inspection_id", "TEXT", "巡检主键"),
            ("site_id", "TEXT", "站点 ID"),
            ("inspection_date", "TEXT", "巡检日期"),
            ("inspector", "TEXT", "巡检人员"),
            ("score", "REAL", "巡检评分"),
            ("issue_count", "INTEGER", "问题数量"),
            ("passed", "INTEGER", "是否通过"),
            ("issue_summary", "TEXT", "问题摘要"),
        ],
    },
]


def get_demo_db_path() -> str:
    return DEMO_DB_PATH


def init_telecom_demo_db() -> None:
    required_tables = {item["name"] for item in TABLE_SCHEMAS}
    if os.path.exists(DEMO_DB_PATH):
        existing = _existing_tables(DEMO_DB_PATH)
        if required_tables.issubset(existing):
            return
        os.remove(DEMO_DB_PATH)

    os.makedirs(os.path.dirname(DEMO_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DEMO_DB_PATH)
    try:
        _create_schema(conn)
        _seed_data(conn)
        conn.commit()
    finally:
        conn.close()


def get_schema_registry() -> List[Dict[str, Any]]:
    return TABLE_SCHEMAS


def get_schema_registry_text() -> str:
    lines = [
        "可用的数据源是一个电信网络运维样例 SQLite 数据库，只能使用下列 10 张表。",
        "如果用户意图不需要某张表，不要强行使用；优先选择列最少、关系最直接的查询路径。",
    ]
    for item in TABLE_SCHEMAS:
        lines.append(f"- {item['name']}: {item['description']}")
        column_desc = "；".join(
            f"{name} ({col_type}, {desc})"
            for name, col_type, desc in item["columns"]
        )
        lines.append(f"  字段: {column_desc}")
    return "\n".join(lines)


def open_demo_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DEMO_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _existing_tables(path: str) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {str(row[0]) for row in rows}
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    ddl_statements = [
        """
        CREATE TABLE dim_region (
            region_id TEXT PRIMARY KEY,
            region_name TEXT NOT NULL,
            province TEXT NOT NULL,
            city_tier TEXT NOT NULL,
            manager_name TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE dim_site (
            site_id TEXT PRIMARY KEY,
            region_id TEXT NOT NULL,
            site_code TEXT NOT NULL,
            site_name TEXT NOT NULL,
            site_type TEXT NOT NULL,
            maintenance_vendor TEXT NOT NULL,
            build_date TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL
        )
        """,
        """
        CREATE TABLE dim_cell (
            cell_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            cell_name TEXT NOT NULL,
            technology TEXT NOT NULL,
            band TEXT NOT NULL,
            carrier TEXT NOT NULL,
            azimuth INTEGER NOT NULL,
            status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE dim_device (
            device_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            cell_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            vendor TEXT NOT NULL,
            model TEXT NOT NULL,
            install_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE fact_asset_inventory (
            asset_id TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            site_id TEXT NOT NULL,
            asset_category TEXT NOT NULL,
            asset_value REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            warranty_expiry TEXT NOT NULL,
            lifecycle_status TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE fact_alarm_event (
            alarm_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            cell_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            alarm_date TEXT NOT NULL,
            first_occurred_at TEXT NOT NULL,
            alarm_severity TEXT NOT NULL,
            alarm_type TEXT NOT NULL,
            cleared INTEGER NOT NULL,
            duration_minutes INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE fact_cell_kpi_daily (
            kpi_id TEXT PRIMARY KEY,
            cell_id TEXT NOT NULL,
            stat_date TEXT NOT NULL,
            prb_utilization REAL NOT NULL,
            downlink_traffic_gb REAL NOT NULL,
            uplink_traffic_gb REAL NOT NULL,
            accessibility_rate REAL NOT NULL,
            retainability_rate REAL NOT NULL,
            drop_call_rate REAL NOT NULL
        )
        """,
        """
        CREATE TABLE fact_traffic_hourly (
            traffic_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            cell_id TEXT NOT NULL,
            stat_hour TEXT NOT NULL,
            traffic_gb REAL NOT NULL,
            peak_users INTEGER NOT NULL,
            packet_loss_rate REAL NOT NULL,
            latency_ms REAL NOT NULL
        )
        """,
        """
        CREATE TABLE fact_work_order (
            work_order_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            cell_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            created_date TEXT NOT NULL,
            closed_date TEXT,
            order_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL,
            sla_breached INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE fact_site_inspection (
            inspection_id TEXT PRIMARY KEY,
            site_id TEXT NOT NULL,
            inspection_date TEXT NOT NULL,
            inspector TEXT NOT NULL,
            score REAL NOT NULL,
            issue_count INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            issue_summary TEXT NOT NULL
        )
        """,
    ]
    for ddl in ddl_statements:
        conn.execute(ddl)


def _seed_data(conn: sqlite3.Connection) -> None:
    rng = random.Random(20260306)
    today = date(2026, 3, 6)

    regions = _seed_regions(conn)
    sites = _seed_sites(conn, rng, regions)
    cells = _seed_cells(conn, rng, sites)
    devices = _seed_devices(conn, rng, cells)
    _seed_assets(conn, rng, today, devices)
    _seed_alarms(conn, rng, today, devices)
    _seed_daily_kpi(conn, rng, today, cells)
    _seed_hourly_traffic(conn, rng, today, cells)
    _seed_work_orders(conn, rng, today, devices)
    _seed_inspections(conn, rng, today, sites)


def _seed_regions(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = [
        ("R01", "华东一片区", "上海", "一线", "张伟"),
        ("R02", "华东二片区", "江苏", "新一线", "刘洋"),
        ("R03", "华南片区", "广东", "一线", "陈晨"),
        ("R04", "华北片区", "北京", "一线", "李峰"),
        ("R05", "西南片区", "四川", "新一线", "周敏"),
        ("R06", "中部片区", "湖北", "二线", "王涛"),
    ]
    conn.executemany(
        "INSERT INTO dim_region(region_id, region_name, province, city_tier, manager_name) VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    return [
        {
            "region_id": region_id,
            "region_name": region_name,
            "province": province,
            "city_tier": city_tier,
            "manager_name": manager_name,
        }
        for region_id, region_name, province, city_tier, manager_name in rows
    ]


def _seed_sites(
    conn: sqlite3.Connection,
    rng: random.Random,
    regions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    site_types = ["宏站", "室分", "楼顶站", "微站"]
    vendors = ["中兴维护", "华为维护", "烽火维护", "诺基亚维护"]
    rows: List[tuple[Any, ...]] = []
    sites: List[Dict[str, Any]] = []
    index = 1
    for region in regions:
        for suffix in range(1, 5):
            site_id = f"S{index:03d}"
            site_code = f"{region['province'][:1]}-{index:03d}"
            site_name = f"{region['province']}{suffix}号站"
            site_type = site_types[(index + suffix) % len(site_types)]
            vendor = vendors[index % len(vendors)]
            build_date = date(2021 + (index % 4), (suffix * 2) % 12 + 1, min(25, suffix * 5)).isoformat()
            latitude = round(24.0 + index * 0.18 + rng.random(), 6)
            longitude = round(102.0 + index * 0.21 + rng.random(), 6)
            rows.append(
                (
                    site_id,
                    region["region_id"],
                    site_code,
                    site_name,
                    site_type,
                    vendor,
                    build_date,
                    latitude,
                    longitude,
                )
            )
            sites.append(
                {
                    "site_id": site_id,
                    "region_id": region["region_id"],
                    "site_name": site_name,
                    "site_type": site_type,
                }
            )
            index += 1
    conn.executemany(
        """
        INSERT INTO dim_site(
            site_id, region_id, site_code, site_name, site_type, maintenance_vendor, build_date, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return sites


def _seed_cells(
    conn: sqlite3.Connection,
    rng: random.Random,
    sites: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    technologies = [("4G", "1.8G"), ("5G", "2.6G"), ("5G", "700M")]
    carriers = ["F1", "F2", "F3", "NR1", "NR2"]
    rows: List[tuple[Any, ...]] = []
    cells: List[Dict[str, Any]] = []
    index = 1
    for site in sites:
        for sector in range(1, 4):
            technology, band = technologies[(sector - 1) % len(technologies)]
            cell_id = f"C{index:04d}"
            cell_name = f"{site['site_name']}-{technology}-扇区{sector}"
            carrier = carriers[(index + sector) % len(carriers)]
            azimuth = ((sector - 1) * 120 + rng.randint(-8, 8)) % 360
            status = "在网" if (index + sector) % 11 else "降级"
            rows.append(
                (
                    cell_id,
                    site["site_id"],
                    cell_name,
                    technology,
                    band,
                    carrier,
                    azimuth,
                    status,
                )
            )
            cells.append(
                {
                    "cell_id": cell_id,
                    "site_id": site["site_id"],
                    "technology": technology,
                    "band": band,
                    "status": status,
                }
            )
            index += 1
    conn.executemany(
        """
        INSERT INTO dim_cell(cell_id, site_id, cell_name, technology, band, carrier, azimuth, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return cells


def _seed_devices(
    conn: sqlite3.Connection,
    rng: random.Random,
    cells: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    vendors = ["华为", "中兴", "爱立信", "诺基亚"]
    rows: List[tuple[Any, ...]] = []
    devices: List[Dict[str, Any]] = []
    index = 1
    for cell in cells:
        site_id = cell["site_id"]
        for device_type in ("BBU", "RRU"):
            device_id = f"D{index:05d}"
            vendor = vendors[index % len(vendors)]
            model = f"{device_type}-{vendor[:2]}-{100 + index % 18}"
            install_date = date(2021 + index % 4, (index % 12) + 1, min(28, (index % 25) + 1)).isoformat()
            status = "在线" if index % 9 else "告警"
            rows.append(
                (
                    device_id,
                    site_id,
                    cell["cell_id"],
                    f"{site_id}-{cell['cell_id']}-{device_type}",
                    device_type,
                    vendor,
                    model,
                    install_date,
                    status,
                )
            )
            devices.append(
                {
                    "device_id": device_id,
                    "site_id": site_id,
                    "cell_id": cell["cell_id"],
                    "device_type": device_type,
                    "vendor": vendor,
                }
            )
            index += 1

    grouped_by_site: Dict[str, str] = {}
    for cell in cells:
        grouped_by_site.setdefault(cell["site_id"], cell["cell_id"])

    for site_idx, (site_id, cell_id) in enumerate(grouped_by_site.items(), start=1):
        device_id = f"D{index:05d}"
        vendor = vendors[(index + site_idx) % len(vendors)]
        rows.append(
            (
                device_id,
                site_id,
                cell_id,
                f"{site_id}-传输设备",
                "传输设备",
                vendor,
                f"TX-{200 + site_idx}",
                date(2020 + site_idx % 4, (site_idx % 12) + 1, 15).isoformat(),
                "在线" if site_idx % 7 else "维护",
            )
        )
        devices.append(
            {
                "device_id": device_id,
                "site_id": site_id,
                "cell_id": cell_id,
                "device_type": "传输设备",
                "vendor": vendor,
            }
        )
        index += 1

    conn.executemany(
        """
        INSERT INTO dim_device(device_id, site_id, cell_id, device_name, device_type, vendor, model, install_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return devices


def _seed_assets(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    devices: List[Dict[str, Any]],
) -> None:
    categories = {
        "BBU": ("无线主设备", 180000),
        "RRU": ("射频设备", 90000),
        "传输设备": ("传输资产", 120000),
    }
    lifecycle_choices = ["在用", "在用", "在用", "待退网", "备件"]
    rows = []
    for idx, device in enumerate(devices, start=1):
        category, base_value = categories.get(device["device_type"], ("其他设备", 50000))
        purchase_date = today - timedelta(days=900 - idx % 240)
        warranty_expiry = purchase_date + timedelta(days=365 * (2 + idx % 3))
        asset_value = round(base_value + rng.randint(-18000, 24000), 2)
        lifecycle = lifecycle_choices[idx % len(lifecycle_choices)]
        rows.append(
            (
                f"A{idx:05d}",
                device["device_id"],
                device["site_id"],
                category,
                asset_value,
                purchase_date.isoformat(),
                warranty_expiry.isoformat(),
                lifecycle,
            )
        )
    conn.executemany(
        """
        INSERT INTO fact_asset_inventory(
            asset_id, device_id, site_id, asset_category, asset_value, purchase_date, warranty_expiry, lifecycle_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_alarms(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    devices: List[Dict[str, Any]],
) -> None:
    severities = ["严重", "重要", "次要", "提示"]
    types = ["断电告警", "光模块异常", "温度过高", "链路中断", "驻波比异常", "传输丢包"]
    rows = []
    alarm_id = 1
    for device in devices:
        count = 1 + (alarm_id % 3)
        for _ in range(count):
            days_ago = rng.randint(0, 29)
            hour = rng.randint(0, 23)
            minute = rng.randint(0, 59)
            occurred = datetime.combine(today - timedelta(days=days_ago), time(hour, minute))
            severity = severities[(alarm_id + days_ago) % len(severities)]
            duration = rng.randint(8, 360)
            cleared = 0 if severity == "严重" and duration > 180 else (1 if rng.random() > 0.25 else 0)
            rows.append(
                (
                    f"AL{alarm_id:06d}",
                    device["site_id"],
                    device["cell_id"],
                    device["device_id"],
                    occurred.date().isoformat(),
                    occurred.isoformat(timespec="minutes"),
                    severity,
                    types[(alarm_id + hour) % len(types)],
                    cleared,
                    duration,
                )
            )
            alarm_id += 1
            if alarm_id > 640:
                break
        if alarm_id > 640:
            break
    conn.executemany(
        """
        INSERT INTO fact_alarm_event(
            alarm_id, site_id, cell_id, device_id, alarm_date, first_occurred_at, alarm_severity, alarm_type, cleared, duration_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_daily_kpi(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    cells: List[Dict[str, Any]],
) -> None:
    rows = []
    kpi_id = 1
    for offset in range(29, -1, -1):
        stat_date = today - timedelta(days=offset)
        for idx, cell in enumerate(cells, start=1):
            base = 52 + (idx % 17) * 1.7
            tech_bias = 11 if cell["technology"] == "5G" else -6
            prb = round(min(98.0, max(18.0, base + tech_bias + rng.uniform(-12, 12))), 2)
            dl = round(max(8.5, prb * 1.35 + rng.uniform(5, 22)), 2)
            ul = round(max(1.8, dl * rng.uniform(0.12, 0.28)), 2)
            access = round(max(93.2, 99.7 - rng.uniform(0, 2.4)), 3)
            retain = round(max(92.8, 99.5 - rng.uniform(0, 2.8)), 3)
            drop_rate = round(max(0.08, min(3.8, 100 - retain + rng.uniform(0, 0.6))), 3)
            if cell["status"] != "在网":
                access = round(max(88.5, access - rng.uniform(1.5, 4.5)), 3)
                retain = round(max(87.8, retain - rng.uniform(2.2, 5.2)), 3)
                drop_rate = round(min(7.8, drop_rate + rng.uniform(0.8, 2.4)), 3)
            rows.append(
                (
                    f"KPI{kpi_id:06d}",
                    cell["cell_id"],
                    stat_date.isoformat(),
                    prb,
                    dl,
                    ul,
                    access,
                    retain,
                    drop_rate,
                )
            )
            kpi_id += 1
    conn.executemany(
        """
        INSERT INTO fact_cell_kpi_daily(
            kpi_id, cell_id, stat_date, prb_utilization, downlink_traffic_gb, uplink_traffic_gb, accessibility_rate, retainability_rate, drop_call_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_hourly_traffic(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    cells: List[Dict[str, Any]],
) -> None:
    rows = []
    traffic_id = 1
    for day_offset in range(6, -1, -1):
        stat_date = today - timedelta(days=day_offset)
        for hour in range(24):
            hour_bias = 1.9 if hour in {20, 21, 22} else (1.35 if hour in {10, 11, 12, 18, 19} else 0.72)
            for idx, cell in enumerate(cells, start=1):
                base = 1.3 + (idx % 9) * 0.38
                traffic = round(max(0.12, base * hour_bias + rng.uniform(0.0, 1.4)), 3)
                peak_users = max(8, int(traffic * 18 + rng.randint(0, 42)))
                packet_loss = round(max(0.02, min(3.6, rng.uniform(0.03, 0.9) + (0.6 if cell["status"] != "在网" else 0))), 3)
                latency = round(max(8.0, 16 + traffic * 4.2 + rng.uniform(-4, 18)), 2)
                rows.append(
                    (
                        f"TF{traffic_id:07d}",
                        cell["site_id"],
                        cell["cell_id"],
                        datetime.combine(stat_date, time(hour, 0)).isoformat(timespec="minutes"),
                        traffic,
                        peak_users,
                        packet_loss,
                        latency,
                    )
                )
                traffic_id += 1
    conn.executemany(
        """
        INSERT INTO fact_traffic_hourly(
            traffic_id, site_id, cell_id, stat_hour, traffic_gb, peak_users, packet_loss_rate, latency_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_work_orders(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    devices: List[Dict[str, Any]],
) -> None:
    order_types = ["巡检整改", "告警处置", "故障抢修", "扩容优化", "资产盘点"]
    priorities = ["P1", "P2", "P3"]
    statuses = ["已关闭", "处理中", "待派发", "已关闭", "已关闭"]
    rows = []
    for idx, device in enumerate(devices[:280], start=1):
        created_date = today - timedelta(days=(idx * 3) % 45)
        status = statuses[idx % len(statuses)]
        closed_date = None
        if status == "已关闭":
            closed_date = (created_date + timedelta(days=1 + idx % 6)).isoformat()
        sla_breached = 1 if status != "已关闭" and idx % 5 == 0 else (1 if status == "已关闭" and idx % 11 == 0 else 0)
        rows.append(
            (
                f"WO{idx:06d}",
                device["site_id"],
                device["cell_id"],
                device["device_id"],
                created_date.isoformat(),
                closed_date,
                order_types[idx % len(order_types)],
                priorities[idx % len(priorities)],
                status,
                sla_breached,
            )
        )
    conn.executemany(
        """
        INSERT INTO fact_work_order(
            work_order_id, site_id, cell_id, device_id, created_date, closed_date, order_type, priority, status, sla_breached
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _seed_inspections(
    conn: sqlite3.Connection,
    rng: random.Random,
    today: date,
    sites: List[Dict[str, Any]],
) -> None:
    inspectors = ["赵倩", "孙浩", "顾铭", "何佳", "韩磊"]
    issue_summaries = [
        "空调温控波动",
        "蓄电池老化",
        "机房卫生需整改",
        "传输线缆标识缺失",
        "接地电阻偏高",
        "未发现明显问题",
    ]
    rows = []
    inspection_id = 1
    for round_idx in range(4):
        for site in sites:
            inspection_date = today - timedelta(days=round_idx * 15 + inspection_id % 6)
            issue_count = (inspection_id + round_idx) % 5
            passed = 0 if issue_count >= 3 and round_idx % 2 == 0 else 1
            score = round(max(72, 98 - issue_count * 4 - rng.uniform(0, 5.5)), 1)
            summary = issue_summaries[(inspection_id + issue_count) % len(issue_summaries)]
            rows.append(
                (
                    f"IN{inspection_id:05d}",
                    site["site_id"],
                    inspection_date.isoformat(),
                    inspectors[inspection_id % len(inspectors)],
                    score,
                    issue_count,
                    passed,
                    summary,
                )
            )
            inspection_id += 1
    conn.executemany(
        """
        INSERT INTO fact_site_inspection(
            inspection_id, site_id, inspection_date, inspector, score, issue_count, passed, issue_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _chunked(items: Iterable[Any], size: int) -> Iterable[List[Any]]:
    bucket: List[Any] = []
    for item in items:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
