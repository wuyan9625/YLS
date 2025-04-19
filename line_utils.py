import json
import sqlite3
from datetime import datetime, timedelta
import os
import requests
import pytz
from math import radians, sin, cos, sqrt, atan2
import qrcode
from io import BytesIO

DB_PATH = 'checkin.db'
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
tz = pytz.timezone("Asia/Taipei")

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
        "messages": [{"type": "text", "text": text}]
    }
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)

def push_image(line_id, image_url):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": line_id,
        "messages": [{
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": image_url
        }]
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
    buffer = BytesIO()
    qrcode.make(json.dumps(config)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def save_qr_image(buffer, filename):
    path = f"static/qr/{filename}"
    with open(path, "wb") as f:
        f.write(buffer.getvalue())

def handle_event(body):
    data = json.loads(body)
    events = data.get("events", [])
    for event in events:
        if event.get("type") == "message":
            line_id = event["source"]["userId"]
            msg = event["message"]["text"].strip()
            process_message(line_id, msg)

def process_message(line_id, msg):
    now = datetime.now(tz)
    now_str = now.strftime("%Y-%m-%d %H:%M")
    now_sql = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE line_id=?", (line_id,))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM user_states WHERE line_id=?", (line_id,))
    state = cursor.fetchone()

    # 教學選項處理 (綁定成功後)
    if msg.lower() == "ios" or msg == "教程":
        push_image(line_id, "https://yls-checkin-bot.onrender.com/static/tutorial/owntracks_ios.png")
        reply_message(line_id, "📄 圖文說明已送出，請依照指示設定 OwnTracks。\nĐã gửi hướng dẫn bằng hình ảnh, vui lòng làm theo.")
        conn.close()
        return

    if msg.lower() == "android":
        cursor.execute("SELECT employee_id FROM users WHERE line_id=?", (line_id,))
        row = cursor.fetchone()
        if row:
            employee_id = row[0]
            filename = f"{employee_id}.png"
            buffer = generate_android_qr_image(employee_id)
            save_qr_image(buffer, filename)
            url = f"https://yls-checkin-bot.onrender.com/static/qr/{filename}"
            push_image(line_id, url)
            reply_message(line_id, "✅ 請打開 OwnTracks 並掃描 QR Code 完成設定。\nVui lòng mở OwnTracks và quét mã QR bên trên.")
        conn.close()
        return

    # 未綁定處理
    if not user:
        if msg in ["上班", "下班", "Đi làm", "Tan làm"]:
            reply_message(line_id, "請先綁定帳號再打卡。\nVui lòng liên kết tài khoản trước khi chấm công.")
        elif not state:
            cursor.execute("INSERT INTO user_states VALUES (?, ?, ?, ?)", (line_id, "awaiting_employee_id", None, now_sql))
            conn.commit()
            reply_message(line_id, "請輸入您的工號：\nVui lòng nhập mã số nhân viên của bạn:")
        elif state[1] == "awaiting_employee_id":
            if not msg.isdigit() or not (2 <= len(msg) <= 3):
                reply_message(line_id, "工號格式錯誤，請輸入 2~3 位數數字。\nMã số nhân viên không hợp lệ, vui lòng nhập lại.")
            else:
                cursor.execute("SELECT * FROM users WHERE employee_id=?", (msg,))
                if cursor.fetchone():
                    reply_message(line_id, "此工號已被其他人使用，請重新輸入。\nMã số đã tồn tại, vui lòng nhập lại.")
                else:
                    cursor.execute("UPDATE user_states SET state='awaiting_name', temp_employee_id=?, last_updated=? WHERE line_id=?", (msg, now_sql, line_id))
                    conn.commit()
                    reply_message(line_id, "請輸入您的姓名：\nVui lòng nhập họ tên của bạn:")
        elif state[1] == "awaiting_name":
            temp_name = msg
            temp_id = state[2]
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (line_id, temp_id, temp_name, now_sql))
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"綁定成功！{temp_name} ({temp_id})\nLiên kết thành công!")
            reply_message(line_id, "請問您使用的是哪一種手機？\nBạn đang sử dụng điện thoại nào？\n\n輸入 iOS → 查看圖文教學\nNhập iOS → Xem hướng dẫn\n\n輸入 Android → 取得 QR 自動設定\nNhập Android → Lấy mã QR để cấu hình tự động")
        conn.close()
        return

    # 打卡相關邏輯開始
    cursor.execute('''SELECT check_type, timestamp FROM checkins
                      WHERE employee_id=? AND DATE(timestamp)=?
                      ORDER BY timestamp''', (user[1], now.strftime("%Y-%m-%d")))
    records = cursor.fetchall()

    # 定位僅限打卡時檢查
    if msg in ["上班", "下班", "Đi làm", "Tan làm"]:
        cursor.execute("SELECT latitude, longitude FROM location_logs WHERE line_id=? ORDER BY timestamp DESC LIMIT 1", (line_id,))
        last_location = cursor.fetchone()
        if not last_location:
            reply_message(line_id, "📍 找不到您的定位資料，請開啟 GPS 並確認 OwnTracks 已設定成功。\nKhông tìm thấy vị trí, vui lòng bật GPS và kiểm tra cấu hình OwnTracks.")
            conn.close()
            return
        if not is_within_allowed_location(*last_location):
            reply_message(line_id, "📍 你不在允許的打卡範圍內，無法打卡。\nBạn không ở khu vực cho phép.")
            conn.close()
            return

    def insert_checkin(t, result):
        cursor.execute('''INSERT INTO checkins (employee_id, name, check_type, timestamp, result)
                          VALUES (?, ?, ?, ?, ?)''', (user[1], user[2], t, now_sql, result))
        conn.commit()

    if msg in ["上班", "Đi làm"]:
        if any(r[0] == "上班" for r in records):
            reply_message(line_id, f"{user[2]}，你今天已打過上班卡。\n{user[2]}, bạn đã chấm công đi làm hôm nay.")
        else:
            insert_checkin("上班", "正常")
            reply_message(line_id, f"{user[2]}，上班打卡成功！\n🔴 時間：{now_str}")
    elif msg in ["下班", "Tan làm"]:
        if not any(r[0] == "上班" for r in records):
            cursor.execute("UPDATE user_states SET state='awaiting_confirm_forgot_checkin', last_updated=? WHERE line_id=?", (now_sql, line_id))
            conn.commit()
            reply_message(line_id, "查無上班紀錄，是否忘記打卡？輸入「確認」補打卡。\nKhông thấy chấm công đi làm, nhập '確認' để xác nhận bổ sung.")
        elif any(r[0] == "下班" for r in records):
            reply_message(line_id, f"{user[2]}，你今天已打過下班卡。\n{user[2]}, bạn đã chấm công tan làm.")
        else:
            start_time = [datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S") for r in records if r[0] == "上班"][0]
            start_time = tz.localize(start_time)
            if now - start_time > timedelta(hours=14):
                insert_checkin("下班", "可能忘記打卡")
            else:
                insert_checkin("下班", "正常")
            reply_message(line_id, f"{user[2]}，下班打卡成功！\n🔴 時間：{now_str}")
    elif msg in ["確認", "Xác nhận"]:
        if state and state[1] == "awaiting_confirm_forgot_checkin":
            insert_checkin("上班", "忘記打卡")
            insert_checkin("下班", "補打卡")
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"{user[2]}，補打上下班卡完成。\n{user[2]}, đã xác nhận và bổ sung chấm công.")
        else:
            reply_message(line_id, "目前無補卡需求。\nKhông có yêu cầu xác nhận.")
    else:
        reply_message(line_id, "請輸入「上班」或「下班」進行打卡。\nVui lòng nhập 'Đi làm' hoặc 'Tan làm' để chấm công.")

    conn.close()
