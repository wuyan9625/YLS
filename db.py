import sqlite3
from datetime import datetime

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

# --- 其他需要的數據操作函數 ---
# 例如查詢打卡狀態，儲存打卡記錄等
