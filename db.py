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

def is_employee_id_taken(employee_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE employee_id = ?", (employee_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def is_line_id_bound(line_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE line_id = ?", (line_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

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
def export_checkins_csv():
    import io
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 抓所有打卡紀錄，照工號 + 日期排序
    cursor.execute("""
        SELECT employee_id, name, check_type, timestamp
        FROM checkins
        ORDER BY employee_id, DATE(timestamp), check_type
    """)
    rows = cursor.fetchall()
    conn.close()

    # 整理資料為：{ 工號: { 日期: {'上班':時間, '下班':時間 } } }
    data = {}
    for emp_id, name, ctype, ts in rows:
        date_str = ts.split(" ")[0]
        time_str = ts.split(" ")[1]
        if emp_id not in data:
            data[emp_id] = {
                "name": name,
                "records": {}
            }
        if date_str not in data[emp_id]["records"]:
            data[emp_id]["records"][date_str] = {"上班": "", "下班": ""}
        if ctype == "上班":
            data[emp_id]["records"][date_str]["上班"] = time_str
        elif ctype == "下班":
            data[emp_id]["records"][date_str]["下班"] = time_str

    # 輸出 CSV 格式
    output = io.StringIO()
    for emp_id, emp_data in data.items():
        output.write(f"工號：{emp_id}\n")
        output.write(f"姓名：{emp_data['name']}\n")
        output.write("日期,上班時間,下班時間\n")
        for date, times in emp_data["records"].items():
            output.write(f"{date},{times['上班']},{times['下班']}\n")
        output.write("\n")  # 員工之間空一行

    return output.getvalue()

