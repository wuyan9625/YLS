import sqlite3
from datetime import datetime

DB_NAME = "checkin.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 使用者主表：正式綁定資料
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT UNIQUE,
            employee_id TEXT UNIQUE,
            name TEXT,
            bind_time TEXT
        )
    """)

    # 打卡記錄表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            line_id TEXT,
            name TEXT,
            check_type TEXT,
            timestamp TEXT,
            latitude REAL,
            longitude REAL,
            distance REAL,
            result TEXT
        )
    """)

    # 使用者暫存綁定狀態表（兩步式流程用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            line_id TEXT PRIMARY KEY,
            state TEXT,
            temp_employee_id TEXT,
            last_updated TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT,
            employee_id TEXT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

def bind_user(line_id, employee_id, name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (line_id, employee_id, name, bind_time) VALUES (?, ?, ?, ?)",
                       (line_id, employee_id, name, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_employee_by_line_id(line_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, name FROM users WHERE line_id = ?", (line_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def has_checked_in_today(employee_id, check_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT * FROM checkins 
        WHERE employee_id = ? AND check_type = ? AND DATE(timestamp) = ?
    """, (employee_id, check_type, today))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_checkin(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checkins (
            employee_id, line_id, name, check_type, timestamp,
            latitude, longitude, distance, result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["employee_id"], data["line_id"], data["name"], data["check_type"], data["timestamp"],
        data["latitude"], data["longitude"], data["distance"], data["result"]
    ))
    conn.commit()
    conn.close()
