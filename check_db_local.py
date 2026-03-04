import sqlite3
import json
import os

db_path = "src/backend/report_system.db"
if not os.path.exists(db_path):
    # Try alternate location if main fails
    db_path = "report_system.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Check table structure first
    cursor.execute("PRAGMA table_info(feedbacks)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Columns in feedbacks: {columns}")
    
    if "images" in columns:
        cursor.execute("SELECT feedback_id, user_ip, content, priority, images FROM feedbacks ORDER BY created_at DESC LIMIT 5")
        rows = cursor.fetchall()
        print(f"Total feedbacks found: {len(rows)}")
        for row in rows:
            images = json.loads(row[4]) if row[4] else []
            print(f"ID: {row[0][:8]} | IP: {row[1]} | Priority: {row[3]} | Content: {row[2][:20]}... | Images: {len(images)}")
    else:
        print("Error: 'images' column missing in feedbacks table.")
    conn.close()
else:
    print(f"Database not found. Searched in several locations.")
