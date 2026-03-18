from __future__ import annotations

import sqlite3
from typing import List

from . import telecom_demo_service


def get_dynamic_options(source: str) -> List[str]:
    mapping = {
        "api:/devices/list": ("dim_device", "device_id"),
        "api:/sites/list": ("dim_site", "site_id"),
        "api:/cells/list": ("dim_cell", "cell_id"),
        "api:/regions/list": ("dim_region", "region_id"),
    }
    if source not in mapping:
        return []
    table, column = mapping[source]
    try:
        telecom_demo_service.init_telecom_demo_db()
        conn = sqlite3.connect(telecom_demo_service.get_demo_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            f"SELECT {column} AS value FROM {table} ORDER BY {column} LIMIT 200"
        )
        rows = [str(row["value"]) for row in cursor.fetchall() if row["value"] is not None]
        conn.close()
        return rows
    except sqlite3.Error:
        return []
