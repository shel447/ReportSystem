from __future__ import annotations

import os
import sqlite3
from typing import List

DB_PATH = os.path.join(os.path.dirname(__file__), "telecom_demo.db")


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
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            f"SELECT {column} AS value FROM {table} ORDER BY {column} LIMIT 200"
        )
        rows = [str(row["value"]) for row in cursor.fetchall() if row["value"] is not None]
        conn.close()
        return rows
    except sqlite3.Error:
        return []
