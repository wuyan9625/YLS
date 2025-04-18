import sqlite3
from datetime import datetime

# --- 資料庫初始化 ---
def init_db():
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()

    # 創建用戶表格（如果不存在）
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        line_id TEXT UNIQUE,
                        emp_id TEXT UNIQUE,
                        name TEXT
                    )''')

    # 創建打卡記錄表格（如果不存在）
    cursor.execute('''CREATE TABLE IF NOT EXISTS checkins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER,
                        line_id TEXT,
                        name TEXT,
                        check_type TEXT,
                        timestamp TEXT,
                        result TEXT,
                        FOREIGN KEY(employee_id) REFERENCES users(id)
                    )''')

    # 創建用戶狀態表格（如果不存在）
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_states (
                        line_id TEXT PRIMARY KEY,
                        state TEXT,
                        temp_employee_id TEXT,
                        last_updated TEXT
                    )''')

    conn.commit()
    conn.close()

# --- 註冊綁定函數 ---
def bind_user(line_id, emp_id, name):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (line_id, emp_id, name) VALUES (?, ?, ?)", (line_id, emp_id, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- 查詢是否已綁定 ---
def is_employee_id_taken(emp_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE emp_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# --- 根據 Line ID 查找用戶 ---
def get_employee_by_line_id(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# --- 檢查是否已經打過上班或下班卡 ---
def has_checked_in_today(employee_id, check_type):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    today_date = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT * FROM checkins WHERE employee_id = ? AND check_type = ? AND timestamp LIKE ?", 
                   (employee_id, check_type, f"{today_date}%"))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# --- 記錄打卡信息 ---
def save_checkin(checkin_data):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO checkins (employee_id, line_id, name, check_type, timestamp, result)
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (checkin_data['employee_id'], checkin_data['line_id'], checkin_data['name'], 
                    checkin_data['check_type'], checkin_data['timestamp'], checkin_data['result']))
    conn.commit()
    conn.close()

# --- 更新用戶狀態 ---
def update_user_state(line_id, state, temp_emp_id=None):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO user_states (line_id, state, temp_employee_id, last_updated) VALUES (?, ?, ?, ?)",
                   (line_id, state, temp_emp_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# --- 清除用戶狀態 ---
def clear_user_state(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_states WHERE line_id = ?", (line_id,))
    conn.commit()
    conn.close()

# --- 查詢用戶狀態 ---
def get_user_state(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT state, temp_employee_id FROM user_states WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "temp_emp_id": row[1]}
    return None
