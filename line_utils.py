import json
import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'checkin.db'

# 模擬允許的打卡地點（可擴充）
ALLOWED_LOCATIONS = [
    (25.0330, 121.5654),  # 台北
    # (10.762622, 106.660172),  # 胡志明市
]

# 檢查是否在允許距離範圍內
def is_within_allowed_location(lat, lng, radius_km=0.5):
    from math import radians, sin, cos, sqrt, atan2
    for allowed_lat, allowed_lng in ALLOWED_LOCATIONS:
        dlat = radians(lat - allowed_lat)
        dlng = radians(lng - allowed_lng)
        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(allowed_lat)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = 6371 * c
        if distance <= radius_km:
            return True
    return False

# 模擬回覆訊息（正式上線可串接 LINE API）
def reply_message(text):
    print(f"[LINE回覆] {text}")

# 主 webhook 處理器
def handle_event(body):
    data = json.loads(body)
    events = data.get("events", [])
    for event in events:
        if event["type"] != "message":
            continue
        line_id = event["source"]["userId"]
        msg = event["message"]["text"].strip()
        process_message(line_id, msg)

# 處理綁定與打卡訊息
def process_message(line_id, msg):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE line_id=?", (line_id,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM user_states WHERE line_id=?", (line_id,))
    state_row = cursor.fetchone()

    if not user:
        # 尚未綁定流程
        if not state_row:
            cursor.execute("INSERT INTO user_states VALUES (?, ?, ?, ?)", (line_id, "awaiting_employee_id", None, datetime.now()))
            conn.commit()
            reply_message("請輸入您的工號：\nVui lòng nhập mã số nhân viên của bạn:")
        elif state_row[1] == "awaiting_employee_id":
            temp_id = msg
            cursor.execute("UPDATE user_states SET state=?, temp_employee_id=?, last_updated=? WHERE line_id=?",
                           ("awaiting_name", temp_id, datetime.now(), line_id))
            conn.commit()
            reply_message("請輸入您的姓名：\nVui lòng nhập họ tên của bạn:")
        elif state_row[1] == "awaiting_name":
            temp_name = msg
            temp_id = state_row[2]
            cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
                           (line_id, temp_id, temp_name, datetime.now()))
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(f"綁定成功！{temp_name} ({temp_id})\nLiên kết thành công!")
        conn.close()
        return

    # 已綁定 → 進入打卡階段
    employee_id, name = user[1], user[2]
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    cursor.execute('''
        SELECT check_type, timestamp FROM checkins
        WHERE employee_id=? AND DATE(timestamp)=?
        ORDER BY timestamp ASC
    ''', (employee_id, today))
    today_records = cursor.fetchall()

    def insert_checkin(check_type, result):
        cursor.execute('''
            INSERT INTO checkins (employee_id, name, check_type, timestamp, result)
            VALUES (?, ?, ?, ?, ?)
        ''', (employee_id, name, check_type, now.strftime("%Y-%m-%d %H:%M:%S"), result))
        conn.commit()

    if msg in ["上班", "Đi làm"]:
        if any(r[0] == "上班" for r in today_records):
            reply_message(f"{name}，你今天已經打過上班卡了。\n{name}, bạn đã chấm công đi làm hôm nay rồi.")
        else:
            insert_checkin("上班", "正常")
            reply_message(f"{name}，上班打卡成功！\n{name}, chấm công đi làm thành công!")

    elif msg in ["下班", "Tan làm"]:
        if not any(r[0] == "上班" for r in today_records):
            # 無上班 → 詢問是否確認補打
            cursor.execute("UPDATE user_states SET state=?, last_updated=? WHERE line_id=?", ("awaiting_confirm_forgot_checkin", now, line_id))
            conn.commit()
            reply_message("查無上班記錄，是否忘記打上班卡？\nBạn quên chấm công đi làm? Gõ '確認' để補打下班卡.")
        elif any(r[0] == "下班" for r in today_records):
            reply_message(f"{name}，你今天已經打過下班卡了。\n{name}, bạn đã chấm công tan làm hôm nay rồi.")
        else:
            checkin_time = datetime.strptime([r[1] for r in today_records if r[0] == "上班"][0], "%Y-%m-%d %H:%M:%S")
            if now - checkin_time > timedelta(hours=14):
                insert_checkin("下班", "可能忘記打卡")
                reply_message(f"{name}，已超過14小時，自動記錄為忘記下班卡。\n{name}, quá 14 tiếng, hệ thống tự ghi nhận.")
            else:
                insert_checkin("下班", "正常")
                reply_message(f"{name}，下班打卡成功！\n{name}, chấm công tan làm thành công!")

    elif msg in ["確認", "Xác nhận"]:
        if state_row and state_row[1] == "awaiting_confirm_forgot_checkin":
            insert_checkin("上班", "忘記打卡")
            insert_checkin("下班", "補打卡")
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(f"{name}，已補記錄上下班。\n{name}, đã xác nhận quên chấm công và ghi nhận lại.")
        else:
            reply_message("目前無需要確認的打卡補記錄。\nKhông có yêu cầu xác nhận nào.")
    else:
        reply_message("請輸入「上班」或「下班」以打卡。\nVui lòng nhập 'Đi làm' hoặc 'Tan làm' để chấm công.")

    conn.close()
