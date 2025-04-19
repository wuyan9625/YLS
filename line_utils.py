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
    (25.0478, 121.5319),  # 可自訂打卡點
]

# 計算兩點間距離（公里）
def is_within_allowed_location(lat, lng, radius_km=0.05):
    for allowed_lat, allowed_lng in ALLOWED_LOCATIONS:
        dlat = radians(lat - allowed_lat)
        dlng = radians(lng - allowed_lng)
        a = sin(dlat/2)**2 + cos(radians(lat)) * cos(radians(allowed_lat)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = 6371 * c  # 地球半徑
        if distance <= radius_km:
            return True
    return False

# 發送訊息到 LINE
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

# 發送圖片到 LINE
def push_image(line_id, image_url):
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    body = {
        "to": line_id,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            }
        ]
    }
    res = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=body)
    if res.status_code != 200:
        print("圖片傳送失敗：", res.status_code, res.text)

# 生成 Android QR 代碼
def generate_android_qr_image(employee_id: str) -> BytesIO:
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

# 儲存 QR 圖片
def save_qr_image(buffer: BytesIO, filename: str):
    path = f"static/qr/{filename}"
    with open(path, "wb") as f:
        f.write(buffer.getvalue())

# 處理 LINE 發送的訊息
def handle_event(body):
    data = json.loads(body)
    events = data.get("events", [])
    for event in events:
        if event["type"] != "message":
            continue
        line_id = event["source"]["userId"]
        msg = event["message"]["text"].strip()
        process_message(line_id, msg)

# 處理用戶的訊息
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
                reply_message(line_id, "工號格式錯誤，請輸入 2~3 位數數字。\nMã số nhân viên không hợp lệ, vui lòng nhập lại.")
            else:
                temp_id = msg
                cursor.execute("SELECT * FROM users WHERE employee_id=?", (temp_id,))
                exists = cursor.fetchone()
                if exists:
                    reply_message(line_id, "此工號已被其他人使用，請重新輸入。\nMã số nhân viên này đã được sử dụng, vui lòng nhập lại.")
                else:
                    cursor.execute("UPDATE user_states SET state=?, temp_employee_id=?, last_updated=? WHERE line_id=?",
                                   ("awaiting_name", temp_id, now_sql, line_id))
                    conn.commit()
                    reply_message(line_id, "請輸入您的姓名：\nVui lòng nhập họ tên của bạn:")
        elif state_row[1] == "awaiting_name":
            temp_name = msg
            temp_id = state_row[2]
            cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (line_id, temp_id, temp_name, now_sql))
            cursor.execute("DELETE FROM user_states WHERE line_id=?", (line_id,))
            conn.commit()
            reply_message(line_id, f"綁定成功！{temp_name} ({temp_id})\nLiên kết thành công!")
            reply_message(line_id,
                "請問您使用的是哪一種手機？\nBạn đang sử dụng loại điện thoại nào？\n\n輸入 iOS → 查看圖文教學\nNhập iOS → Xem hướng dẫn\n\n輸入 Android → 取得 QR 自動設定\nNhập Android → Lấy mã QR để cài đặt tự động")
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
            reply_message(line_id, "查無上班記錄，是否忘記打上班卡？\nBạn quên chấm công đi làm? Gõ '確認' để补打下班卡.")
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
    elif msg.lower() == "android":
        filename = f"{employee_id}.png"
        buffer = generate_android_qr_image(employee_id)
        save_qr_image(buffer, filename)
        qr_url = f"https://yls-checkin-bot.onrender.com/static/qr/{filename}"
        push_image(line_id, qr_url)
        reply_message(line_id, "✅ 請打開 OwnTracks 並掃描上方 QR Code 完成設定。\nVui lòng mở OwnTracks và quét mã QR bên trên để hoàn tất thiết lập.")
    elif msg.lower() == "ios" or msg == "教程":
        image_url = "https://yls-checkin-bot.onrender.com/static/tutorial/owntracks_ios.png"
        push_image(line_id, image_url)
        reply_message(line_id, "📄 圖文說明已送出，請依照指示設定 OwnTracks。\nĐã gửi hướng dẫn bằng hình ảnh, vui lòng làm theo để cấu hình OwnTracks.")
    else:
        reply_message(line_id, "請輸入「上班」或「下班」以打卡。\nVui lòng nhập 'Đi làm' hoặc 'Tan làm' để chấm công.")

    conn.close()
