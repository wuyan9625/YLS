import sqlite3
from datetime import datetime
import csv
import io

DB_NAME = "checkin.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 使用者
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT UNIQUE,
            employee_id TEXT UNIQUE,
            name TEXT,
            bind_time TEXT
        )
    """)

    # 打卡紀錄（不包含地點）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            line_id TEXT,
            name TEXT,
            check_type TEXT,
            timestamp TEXT,
            result TEXT
        )
    """)

    # 定位日誌
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            name TEXT,
            line_id TEXT,
            latitude REAL,
            longitude REAL,
            timestamp TEXT,
            distance REAL,
            source TEXT
        )
    """)

    # 綁定狀態暫存
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

# === 綁定與查詢 ===
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

# === 打卡與定位記錄 ===
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
            employee_id, line_id, name, check_type, timestamp, result
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["employee_id"], data["line_id"], data["name"],
        data["check_type"], data["timestamp"], data["result"]
    ))
    conn.commit()
    conn.close()

def save_location_log(employee_id, name, line_id, lat, lng, timestamp, distance, source="OwnTracks"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO location_logs (
            employee_id, name, line_id, latitude, longitude, timestamp, distance, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (employee_id, name, line_id, lat, lng, timestamp, distance, source))
    conn.commit()
    conn.close()

# === 匯出打卡報表（可選月）===
def export_checkins_summary_csv(month=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if month:
        cursor.execute("""
            SELECT employee_id, name, check_type, timestamp
            FROM checkins
            WHERE strftime('%Y-%m', timestamp) = ?
            ORDER BY employee_id, DATE(timestamp), check_type
        """, (month,))
    else:
        cursor.execute("""
            SELECT employee_id, name, check_type, timestamp
            FROM checkins
            ORDER BY employee_id, DATE(timestamp), check_type
        """)

    rows = cursor.fetchall()
    conn.close()

    summary = {}
    for emp_id, name, ctype, ts in rows:
        date = ts[:10]
        if emp_id not in summary:
            summary[emp_id] = {"name": name, "records": {}}
        if date not in summary[emp_id]["records"]:
            summary[emp_id]["records"][date] = {"上班": "", "下班": ""}
        summary[emp_id]["records"][date][ctype] = ts[11:]

    output = io.StringIO()
    writer = csv.writer(output)
    for emp_id, emp_data in summary.items():
        writer.writerow([f"工號：{emp_id}", f"姓名：{emp_data['name']}"])
        writer.writerow(["日期", "上班時間", "下班時間"])
        for date, record in emp_data["records"].items():
            writer.writerow([date, record["上班"], record["下班"]])
        writer.writerow([])

    return output.getvalue()

# === 匯出定位紀錄（可選月）===
def export_location_logs_csv(month=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if month:
        cursor.execute("""
            SELECT employee_id, name, line_id, latitude, longitude, timestamp, distance, source
            FROM location_logs
            WHERE strftime('%Y-%m', timestamp) = ?
            ORDER BY timestamp DESC
        """, (month,))
    else:
        cursor.execute("""
            SELECT employee_id, name, line_id, latitude, longitude, timestamp, distance, source
            FROM location_logs
            ORDER BY timestamp DESC
        """)

    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工號", "姓名", "Line ID", "緯度", "經度", "時間", "距離（公尺）", "來源"])
    writer.writerows(rows)
    return output.getvalue()
