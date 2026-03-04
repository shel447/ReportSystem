import sqlite3
import os

db_path = "src/backend/report_system.db"
if not os.path.exists(db_path):
    db_path = "report_system.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(feedbacks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "submitter" not in columns:
            print("Adding 'submitter' column to feedbacks table...")
            cursor.execute("ALTER TABLE feedbacks ADD COLUMN submitter TEXT")
            conn.commit()
            print("Column 'submitter' added successfully.")
        else:
            print("Column 'submitter' already exists.")
    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        conn.close()
else:
    print("Database not found for migration.")
