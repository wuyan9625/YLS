import json
import sqlite3
from datetime import datetime, timedelta
import os
import requests
import pytz
from math import radians, sin, cos, sqrt, atan2
# line_utils.py - 整合綁定、打卡、定位驗證、LINE回覆、QR生成功能

import json
import sqlite3
from datetime import datetime, timedelta
import os
import requests
import pytz
import qrcode
from math import radians, sin, cos, sqrt, atan2
from io import BytesIO

DB_PATH = 'checkin.db'
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
tz = pytz.timezone("Asia/Taipei")

# 打卡允許範圍（台北車站為例）
ALLOWED_LOCATIONS = [
    (25.0478, 121.5319),
]

def is_within_allowed_location(lat, lng, radius_km=0.05):
    for allowed_lat, allowed_lng in ALLOWED_LOCATIONS:
        dlat = radians(lat - allowed_lat)
        dlng = radians(lng - allowed_lng)
        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(allowed_lat)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c
        if distance <= radius_km:
            return True
    return False

def reply_message(line_id, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "to": line_id,
        "messages": [
            {"type": "text", "text": text}
        ]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)

def generate_android_qr_image(employee_id):
    config = {
        "_type": "configuration",
        "desc": f"YLS 打卡設定 - 工號 {employee_id}",
        "url": "https://yls-checkin-bot.onrender.com/location/webhook",
        "ident": employee_id,
        "trackerId": "ot",
        "secret": False
    }
    qr_data = json.dumps(config)
    qr_img = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def handle_event(body):
    data = json.loads(body)
    events = data.get("events", [])
    for event in events:
        if event["type"] != "message":
            continue
        line_id = event["source"]["userId"]
        msg = event["message"]["text"].strip()
        process_message(line_id, msg)

def process_message(line_id, msg):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE line_id=?", (line_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM user_states WHERE line_id=?", (line_id,))
    state_row = cursor.fetchone()

    now = datetime.now(tz)
    now_str = now.strftime("%Y-%m-%d %H:%M")
    now_sql = now.strftime("%Y-%m-%d %H:%M:%S")

    if not user:
        if msg in ["上班", "下班", "Đi làm", "Tan làm"]:
            reply_message(line_id, "請先綁定帳號再打卡\nVui lòng liên kết tài khoản trước khi chấm công.")
            conn.close()
            return
        if not state_row:
            cursor.execute("INSERT INTO user_states VALUES (?, ?, ?, ?)", (line_id, "awaiting_employee_id", None, now_sql))
            conn.commit()
            reply_message(line_id, "請輸入您的工號\nVui lòng nhập mã số nhân viên của bạn:")
        elif state_row[1] == "awaiting_employee_id":
            if not msg.isdigit() or not (2 <= len(msg) <= 3):
                reply_message(line_id, "工號不正確，請輸入2~3位數字\nMã số không hợp lệ, vui lòng nhập lại.")
            else:
                temp_id = msg
                cursor.execute("SELECT * FROM users WHERE employee_id=?", (temp_id,))
                if cursor.fetchone():
                    reply_message(line_id, "此工號已被使用\nMã số này đã được sử dụng")
                else:
                    cursor.execute("UPDATE user_states SET state=?, temp_employee_id=?, last_updated=? WHERE line_id=?",
                                   ("awaiting_name", temp_id, now_sql, line_id))
                    conn.commit()
                    reply_message(line_id, "請輸入姓名\nVui lòng nhập họ tên:")
        elif state_row[1] == "awaiting_name":
            temp_name = msg
            temp_id = state_row[2]
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (line_id, temp_id, temp_name, now_sql))
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"綁定成功！{temp_name} ({temp_id})\nLiên kết thành công!")
        conn.close()
        return

    employee_id, name = user[1], user[2]
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
        ''', (employee_id, name, check_type, now_sql, result))
        conn.commit()

    cursor.execute("SELECT latitude, longitude FROM location_logs WHERE line_id=? ORDER BY timestamp DESC LIMIT 1", (line_id,))
    last_location = cursor.fetchone()
    if not last_location:
        reply_message(line_id, "📍 找不到您的定位，請開啟 GPS\nVui lòng bật GPS để chấm công")
        conn.close()
        return

    lat, lng = last_location
    if not is_within_allowed_location(lat, lng):
        reply_message(line_id, "📍 位置不在允許範圍\nBạn không ở khu vực chấm công")
        conn.close()
        return

    if msg in ["\u4e0a\u73ed", "\u0110i l\u00e0m"]:
        if any(r[0] == "\u4e0a\u73ed" for r in today_records):
            reply_message(line_id, f"{name}，你今天已經打過上班卡\n{name}, bạn đã chấm công đi làm hôm nay")
        else:
            insert_checkin("\u4e0a\u73ed", "\u6b63常")
            reply_message(line_id, f"{name}，上班打卡成功！\n🔴 時間：{now_str}\n{name}, chấm công đi làm thành công!")

    elif msg in ["\u4e0b\u73ed", "Tan l\u00e0m"]:
        if not any(r[0] == "\u4e0a\u73ed" for r in today_records):
            cursor.execute("UPDATE user_states SET state=?, last_updated=? WHERE line_id=?",
                           ("awaiting_confirm_forgot_checkin", now_sql, line_id))
            conn.commit()
            reply_message(line_id, "查無上班記錄，是否忘記打卡？\nBạn quên chấm công đi làm? Gõ '確認' để bổ sung.")
        elif any(r[0] == "\u4e0b\u73ed" for r in today_records):
            reply_message(line_id, f"{name}，你今天已經打過下班卡\n{name}, bạn đã chấm công tan làm hôm nay")
        else:
            checkin_time = datetime.strptime([r[1] for r in today_records if r[0] == "上班"][0], "%Y-%m-%d %H:%M:%S")
            checkin_time = tz.localize(checkin_time)
            if now - checkin_time > timedelta(hours=14):
                insert_checkin("\u4e0b\u73ed", "\u53ef能忘記")
                reply_message(line_id, f"{name}，已超過14小時，自動記錄為忘記下班\n🔴 時間：{now_str}\n{name}, quá 14 tiếng, hệ thống tự ghi nhận.")
            else:
                insert_checkin("\u4e0b\u73ed", "\u6b63常")
                reply_message(line_id, f"{name}，下班打卡成功！\n🔴 時間：{now_str}\n{name}, chấm công tan làm thành công!")

    elif msg in ["確認", "Xác nhận"]:
        if state_row and state_row[1] == "awaiting_confirm_forgot_checkin":
            insert_checkin("\u4e0a\u73ed", "\u5fd8\u8a18\u6253\u5361")
            insert_checkin("\u4e0b\u73ed", "\u88dc\u6253\u5361")
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"{name}，已補記錄\n{name}, đã xác nhận quên chấm công.")
        else:
            reply_message(line_id, "目前無需要確認的記錄\nKhông có yêu cầu xác nhận.")

    else:
        reply_message(line_id, "請輸入「上班」或「下班」\nVui lòng nhập 'Di lam' hoặc 'Tan lam'")

    conn.close()

DB_PATH = 'checkin.db'
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
tz = pytz.timezone("Asia/Taipei")

# 台北車站為範例，可加入多個打卡點
ALLOWED_LOCATIONS = [
    (25.0478, 121.5319),  # 可自訂打卡點
]

# 計算兩點間距離（公里）
def is_within_allowed_location(lat, lng, radius_km=0.05):
    for allowed_lat, allowed_lng in ALLOWED_LOCATIONS:
        dlat = radians(lat - allowed_lat)
        dlng = radians(lng - allowed_lng)
        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(allowed_lat)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c
        if distance <= radius_km:
            return True
    return False

def reply_message(line_id, text):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "to": line_id,
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=body
    )
    if response.status_code != 200:
        print("LINE 傳送失敗：", response.status_code, response.text)

def handle_event(body):
    data = json.loads(body)
    events = data.get("events", [])
    for event in events:
        if event["type"] != "message":
            continue
        line_id = event["source"]["userId"]
        msg = event["message"]["text"].strip()
        process_message(line_id, msg)

def process_message(line_id, msg):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE line_id=?", (line_id,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM user_states WHERE line_id=?", (line_id,))
    state_row = cursor.fetchone()

    now = datetime.now(tz)
    now_str = now.strftime("%Y-%m-%d %H:%M")
    now_sql = now.strftime("%Y-%m-%d %H:%M:%S")

    if not user:
        if msg in ["上班", "下班", "Đi làm", "Tan làm"]:
            reply_message(line_id, "請先綁定帳號再打卡。\nVui lòng liên kết tài khoản trước khi chấm công.")
            conn.close()
            return

        if not state_row:
            cursor.execute("INSERT INTO user_states VALUES (?, ?, ?, ?)", (line_id, "awaiting_employee_id", None, now_sql))
            conn.commit()
            reply_message(line_id, "請輸入您的工號：\nVui lòng nhập mã số nhân viên của bạn:")
        elif state_row[1] == "awaiting_employee_id":
            if not msg.isdigit() or not (2 <= len(msg) <= 3):
                reply_message(line_id, "工號是不是輸入錯誤？請輸入2~3位數字工號。\nMã số nhân viên không hợp lệ, vui lòng nhập lại bằng số từ 2-3 chữ số.")
            else:
                temp_id = msg
                cursor.execute("SELECT * FROM users WHERE employee_id=?", (temp_id,))
                exists = cursor.fetchone()
                if exists:
                    reply_message(line_id, "此工號已被其他人使用，請使用其他工號。\nMã số nhân viên này đã được sử dụng, vui lòng nhập lại.")
                else:
                    cursor.execute("UPDATE user_states SET state=?, temp_employee_id=?, last_updated=? WHERE line_id=?",
                                   ("awaiting_name", temp_id, now_sql, line_id))
                    conn.commit()
                    reply_message(line_id, "請輸入您的姓名：\nVui lòng nhập họ tên của bạn:")
        elif state_row[1] == "awaiting_name":
            temp_name = msg
            temp_id = state_row[2]
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                           (line_id, temp_id, temp_name, now_sql))
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"綁定成功！{temp_name} ({temp_id})\nLiên kết thành công!")
        conn.close()
        return

    employee_id, name = user[1], user[2]
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
        ''', (employee_id, name, check_type, now_sql, result))
        conn.commit()

    # 新增：取得最後定位紀錄，檢查距離
    cursor.execute("SELECT latitude, longitude FROM location_logs WHERE line_id=? ORDER BY timestamp DESC LIMIT 1", (line_id,))
    last_location = cursor.fetchone()
    if not last_location:
        reply_message(line_id, "📍 找不到您的定位資料，請開啟 GPS 並確認 OwnTracks 已設定成功。\nKhông tìm thấy vị trí, vui lòng bật GPS và đảm bảo đã cấu hình OwnTracks.")
        conn.close()
        return

    lat, lng = last_location
    if not is_within_allowed_location(lat, lng):
        reply_message(line_id, "📍 你不在允許的打卡範圍內，無法打卡。\nBạn không ở khu vực chấm công cho phép.")
        conn.close()
        return

    if msg in ["上班", "Đi làm"]:
        if any(r[0] == "上班" for r in today_records):
            reply_message(line_id, f"{name}，你今天已經打過上班卡了。\n{name}, bạn đã chấm công đi làm hôm nay rồi.")
        else:
            insert_checkin("上班", "正常")
            reply_message(line_id, f"{name}，上班打卡成功！\n🔴 時間：{now_str}\n{name}, chấm công đi làm thành công!")

    elif msg in ["下班", "Tan làm"]:
        if not any(r[0] == "上班" for r in today_records):
            cursor.execute("UPDATE user_states SET state=?, last_updated=? WHERE line_id=?",
                           ("awaiting_confirm_forgot_checkin", now_sql, line_id))
            conn.commit()
            reply_message(line_id, "查無上班記錄，是否忘記打上班卡？\nBạn quên chấm công đi làm? Gõ '確認' để補打下班卡.")
        elif any(r[0] == "下班" for r in today_records):
            reply_message(line_id, f"{name}，你今天已經打過下班卡了。\n{name}, bạn đã chấm công tan làm hôm nay rồi.")
        else:
            checkin_time = datetime.strptime([r[1] for r in today_records if r[0] == "上班"][0], "%Y-%m-%d %H:%M:%S")
            checkin_time = tz.localize(checkin_time)
            if now - checkin_time > timedelta(hours=14):
                insert_checkin("下班", "可能忘記打卡")
                reply_message(line_id, f"{name}，已超過14小時，自動記錄為忘記下班卡。\n🔴 時間：{now_str}\n{name}, quá 14 tiếng, hệ thống tự ghi nhận.")
            else:
                insert_checkin("下班", "正常")
                reply_message(line_id, f"{name}，下班打卡成功！\n🔴 時間：{now_str}\n{name}, chấm công tan làm thành công!")

    elif msg in ["確認", "Xác nhận"]:
        if state_row and state_row[1] == "awaiting_confirm_forgot_checkin":
            insert_checkin("上班", "忘記打卡")
            insert_checkin("下班", "補打卡")
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"{name}，已補記錄上下班。\n{name}, đã xác nhận quên chấm công và ghi nhận lại.")
        else:
            reply_message(line_id, "目前無需要確認的打卡補記錄。\nKhông có yêu cầu xác nhận nào.")

    else:
        reply_message(line_id, "請輸入「上班」或「下班」以打卡。\nVui lòng nhập 'Đi làm' hoặc 'Tan làm' để chấm công.")

    conn.close()
