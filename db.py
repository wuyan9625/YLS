import sqlite3
from datetime import datetime

# 建立資料庫連接
def create_connection():
    conn = sqlite3.connect("checkin.db")  # 此處為資料庫檔案名稱，可以根據需求更改
    return conn

# 初始化資料庫及資料表
def init_db():
    conn = create_connection()
    cursor = conn.cursor()
    
    # 創建 users 表，存儲用戶的 LINE ID 和工號
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            name TEXT
        )
    """)
    
    # 創建 checkin 表，存儲用戶的打卡記錄
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            check_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            result TEXT
        )
    """)
    
    # 創建 user_states 表，存儲用戶的狀態（例如工號綁定進程）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            line_id TEXT PRIMARY KEY,
            state TEXT,
            temp_employee_id TEXT,
            last_updated TEXT
        )
    """)
    
    # 提交並關閉連接
    conn.commit()
    conn.close()

# 查找是否已有用戶綁定
def get_employee_by_line_id(line_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# 檢查工號是否已經被綁定
def is_employee_id_taken(emp_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE employee_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# 綁定用戶與工號
def bind_user(line_id, emp_id, name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (line_id, employee_id, name) VALUES (?, ?, ?)", (line_id, emp_id, name))
    conn.commit()
    conn.close()
    return True

# 保存打卡紀錄
def save_checkin(data):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checkin (employee_id, check_type, timestamp, result)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['check_type'], data['timestamp'], data['result']))
    conn.commit()
    conn.close()

# 檢查用戶是否已經打過卡
def has_checked_in_today(employee_id, check_type):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM checkin WHERE employee_id = ? AND check_type = ? AND DATE(timestamp) = DATE('now')", (employee_id, check_type))
    row = cursor.fetchone()
    conn.close()
    return row is not None

# 用戶狀態管理：獲取用戶狀態
def get_user_state(line_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT state, temp_employee_id FROM user_states WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "temp_emp_id": row[1]}
    return None

# 更新用戶狀態
def update_user_state(line_id, state, temp_emp_id=None):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO user_states (line_id, state, temp_employee_id, last_updated) VALUES (?, ?, ?, ?)",
                   (line_id, state, temp_emp_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# 清除用戶狀態
def clear_user_state(line_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_states WHERE line_id = ?", (line_id,))
    conn.commit()
    conn.close()