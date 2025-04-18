import sqlite3
from datetime import datetime

def init_db():
    # 連接到 SQLite 數據庫（若數據庫文件不存在，會自動創建）
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()

    # 創建 users 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT NOT NULL,
            employee_id TEXT,
            name TEXT
        )
    """)

    # 創建 checkin 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            check_type TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)

    # 創建 user_states 表格（如果尚未存在）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            line_id TEXT PRIMARY KEY,
            state TEXT,
            temp_employee_id TEXT,
            last_updated TEXT
        )
    """)

    # 提交更改並關閉連接
    conn.commit()
    conn.close()

def bind_user(line_id, emp_id, name):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (line_id, employee_id, name) VALUES (?, ?, ?)", (line_id, emp_id, name))
    conn.commit()
    conn.close()
