import sqlite3

def init_db():
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()

    # 使用者綁定資訊
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        line_id TEXT PRIMARY KEY,
        employee_id TEXT UNIQUE,
        name TEXT,
        bind_time TEXT
    )
    ''')

    # 使用者當前狀態（註冊流程狀態、暫存資料）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
        line_id TEXT PRIMARY KEY,
        state TEXT,
        temp_employee_id TEXT,
        last_updated TEXT
    )
    ''')

    # 打卡記錄
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checkins (
        employee_id TEXT,
        name TEXT,
        check_type TEXT,
        timestamp TEXT,
        result TEXT
    )
    ''')

    # 定位資料記錄
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS location_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id TEXT,
        employee_id TEXT,
        name TEXT,
        latitude REAL,
        longitude REAL,
        timestamp TEXT
    )
    ''')

    conn.commit()
    conn.close()
