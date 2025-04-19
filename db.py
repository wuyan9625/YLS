import sqlite3

def init_db():
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()

    # 綁定的使用者資料
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        line_id TEXT PRIMARY KEY,
        employee_id TEXT UNIQUE,
        name TEXT,
        bind_time TEXT
    )
    ''')

    # 使用者狀態（綁定流程、補打卡流程）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
        line_id TEXT PRIMARY KEY,
        state TEXT,
        temp_employee_id TEXT,
        last_updated TEXT
    )
    ''')

    # 打卡紀錄表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT,
        name TEXT,
        check_type TEXT, -- 上班 / 下班
        timestamp TEXT,
        result TEXT       -- 正常 / 忘記打卡 / 補打卡 / 可能忘記打卡
    )
    ''')

    # 定位紀錄表（OwnTracks）
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
