import sqlite3
from datetime import datetime

# 資料庫初始化
def init_db():
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    # 創建 users 表格
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        line_id TEXT PRIMARY KEY,
        employee_id TEXT UNIQUE,
        name TEXT,
        bind_time TEXT
    )
    ''')
    # 創建 user_states 表格
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_states (
        line_id TEXT PRIMARY KEY,
        state TEXT,
        temp_employee_id TEXT,
        last_updated TEXT
    )
    ''')
    # 創建 checkins 表格
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS checkins (
        employee_id TEXT,
        line_id TEXT,
        name TEXT,
        check_type TEXT,
        timestamp TEXT,
        result TEXT
    )
    ''')
    conn.commit()
    conn.close()

# 更新使用者狀態
def update_user_state(line_id, state, temp_emp_id=None):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO user_states (line_id, state, temp_employee_id, last_updated)
        VALUES (?, ?, ?, ?)
    ''', (line_id, state, temp_emp_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# 取得使用者狀態
def get_user_state(line_id):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT state, temp_employee_id FROM user_states WHERE line_id = ?', (line_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "temp_emp_id": row[1]}
    return None

# 清除使用者狀態
def clear_user_state(line_id):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_states WHERE line_id = ?', (line_id,))
    conn.commit()
    conn.close()

# 檢查員工ID是否已被綁定
def is_employee_id_taken(emp_id):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT line_id FROM users WHERE employee_id = ?', (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# 綁定員工
def bind_user(line_id, emp_id, name):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (line_id, employee_id, name, bind_time) VALUES (?, ?, ?, ?)', 
                   (line_id, emp_id, name, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True

# 確認今天是否已經打卡
def has_checked_in_today(employee_id, check_type):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM checkins WHERE employee_id = ? AND check_type = ? AND DATE(timestamp) = DATE("now")', (employee_id, check_type))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# 儲存打卡記錄
def save_checkin(checkin_data):
    conn = sqlite3.connect('checkin.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO checkins (employee_id, line_id, name, check_type, timestamp, result)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (checkin_data['employee_id'], checkin_data['line_id'], checkin_data['name'], checkin_data['check_type'], checkin_data['timestamp'], checkin_data['result']))
    conn.commit()
    conn.close()