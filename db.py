import sqlite3
from datetime import datetime

# 建立資料庫連接
def create_connection():
    conn = sqlite3.connect("checkin.db")
    return conn

# 檢查 line_id 是否已經綁定
def is_line_id_bound(line_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None  # 如果找到了該 line_id，則返回 True，表示已經綁定

# 根據 line_id 查詢用戶
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

# 儲存打卡紀錄
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