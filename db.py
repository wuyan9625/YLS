import sqlite3
from datetime import datetime, timedelta
import calendar

DB_NAME = "checkin.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT UNIQUE,
            employee_id TEXT UNIQUE,
            name TEXT,
            bind_time TEXT
        )
    """)

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

def export_checkins_csv(month: str = None):
    import io
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if month:
        year, mon = map(int, month.split("-"))
        start_date = f"{year}-{mon:02d}-01"
        end_day = calendar.monthrange(year, mon)[1]
        end_date = f"{year}-{mon:02d}-{end_day}"
    else:
        today = datetime.now()
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
        end_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=end_day).strftime("%Y-%m-%d")
        month = today.strftime("%Y-%m")

    # 所有已綁定使用者
    cursor.execute("SELECT employee_id, name FROM users ORDER BY employee_id")
    users = cursor.fetchall()

    # 抓所有該月打卡紀錄
    cursor.execute("""
        SELECT employee_id, check_type, timestamp FROM checkins 
        WHERE DATE(timestamp) BETWEEN ? AND ?
    """, (start_date, end_date))
    checkins = cursor.fetchall()
    conn.close()

    # 整理打卡紀錄到 dict[工號][日期] = {上班:時間, 下班:時間}
    records = {}
    for emp_id, ctype, ts in checkins:
        date = ts.split(" ")[0]
        time = ts.split(" ")[1]
        if emp_id not in records:
            records[emp_id] = {}
        if date not in records[emp_id]:
            records[emp_id][date] = {"上班": "", "下班": ""}
        records[emp_id][date][ctype] = time

    # 輸出格式
    output = io.StringIO()
    for emp_id, name in users:
        output.write(f"工號：{emp_id}\n")
        output.write(f"姓名：{name}\n")
        output.write(f"月份：{month}\n")
        output.write("日期,上班時間,下班時間\n")

        # 該月每一天
        year, mon = map(int, month.split("-"))
        for day in range(1, calendar.monthrange(year, mon)[1] + 1):
            date_str = f"{year}-{mon:02d}-{day:02d}"
            r = records.get(emp_id, {}).get(date_str, {"上班": "", "下班": ""})
            output.write(f"{date_str},{r['上班']},{r['下班']}\n")

        output.write("\n")  # 員工之間空一行

    return output.getvalue()
