import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT NOT NULL,
            employee_id TEXT,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            check_type TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            line_id TEXT PRIMARY KEY,
            state TEXT,
            temp_employee_id TEXT,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

def bind_user(line_id, emp_id, name):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (line_id, employee_id, name) VALUES (?, ?, ?)", (line_id, emp_id, name))
    conn.commit()
    conn.close()
    return True

def get_employee_by_line_id(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def is_employee_id_taken(emp_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE employee_id = ?", (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_checkin(data):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checkin (employee_id, check_type, timestamp, result)
        VALUES (?, ?, ?, ?)
    """, (data['employee_id'], data['check_type'], data['timestamp'], data['result']))
    conn.commit()
    conn.close()
