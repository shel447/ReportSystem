import sqlite3
import os

db_path = "src/backend/report_system.db"
if not os.path.exists(db_path):
    db_path = "report_system.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if column exists first
        cursor.execute("PRAGMA table_info(feedbacks)")
        columns = [row[1] for row in cursor.fetchall()]
        if "images" not in columns:
            print("Adding 'images' column to feedbacks table...")
            cursor.execute("ALTER TABLE feedbacks ADD COLUMN images JSON DEFAULT '[]'")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'images' already exists.")
    except Exception as e:
        print(f"Error during migration: {str(e)}")
    finally:
        conn.close()
else:
    print("Database not found for migration.")
