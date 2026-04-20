from __future__ import annotations

import sqlite3
from typing import Any, List

from . import telecom


def get_dynamic_options(source: str) -> List[str]:
    return [str(item["label"]) for item in get_dynamic_option_items(source)]


def get_dynamic_option_items(source: str) -> List[dict[str, Any]]:
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
        telecom.init_telecom_demo_db()
        conn = sqlite3.connect(telecom.get_demo_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            f"SELECT {column} AS value FROM {table} ORDER BY {column} LIMIT 200"
        )
        rows = [
            {
                "label": str(row["value"]),
                "value": str(row["value"]),
                "query": str(row["value"]),
            }
            for row in cursor.fetchall()
            if row["value"] is not None
        ]
        conn.close()
        return rows
    except sqlite3.Error:
        return []
