import sqlite3
import hmac
import json
import requests
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from db import (
    bind_user, get_employee_by_line_id, is_employee_id_taken,
    is_line_id_bound, save_checkin, has_checked_in_today, init_db
)

# 公司座標與設定
COMPANY_LAT = 24.4804401433383
COMPANY_LNG = 120.7956030766374
ALLOWED_RADIUS_M = 50

# ✅ 處理整包 webhook events 陣列
def handle_event(body, signature, channel_secret, channel_token):
    events = body.get("events", [])
    for event in events:
        process_event(event, channel_secret, channel_token)

# ✅ 單筆事件處理邏輯
def process_event(event, channel_secret, channel_token):
    event_type = event.get("type")
    message = event.get("message", {})
    reply_token = event.get("replyToken")
    line_id = event.get("source", {}).get("userId")

    if event_type == "message" and message.get("type") == "text":
        text = message.get("text").strip()

        # 啟動綁定流程
        if text in ["綁定", "我要綁定", "gắn mã", "gắn", "bind"]:
            update_user_state(line_id, "WAIT_EMP_ID")
            reply_message(reply_token, "📋 請輸入您的工號（mã nhân viên）", channel_token)
            return

        # 根據綁定狀態處理輸入
        state_info = get_user_state(line_id)
        if state_info:
            state = state_info["state"]
            if state == "WAIT_EMP_ID":
                emp_id = text
                if is_employee_id_taken(emp_id):
                    reply_message(reply_token, "❌ 此工號已被其他人綁定！\n❌ Mã nhân viên đã được sử dụng!", channel_token)
                    return
                update_user_state(line_id, "WAIT_NAME", temp_emp_id=emp_id)
                reply_message(reply_token, "📋 請輸入您的姓名（tên）", channel_token)
                return

            elif state == "WAIT_NAME":
                emp_id = state_info["temp_emp_id"]
                name = text
                success = bind_user(line_id, emp_id, name)
                if success:
                    reply_message(reply_token,
                        f"✅ 綁定成功！工號：{emp_id}，姓名：{name}\n✅ Đã gắn mã nhân viên: {emp_id}, tên: {name}",
                        channel_token)
                else:
                    reply_message(reply_token, "❌ 綁定失敗，請重新嘗試", channel_token)
                clear_user_state(line_id)
                return

        # 上班 / 下班打卡提示
        if text in ["上班", "下班"]:
            reply_message(reply_token, f"📍 請傳送您目前的位置以進行【{text}】打卡", channel_token)

    # 定位打卡處理
    elif event_type == "message" and message.get("type") == "location":
        lat, lng = message["latitude"], message["longitude"]
        distance = calculate_distance(lat, lng, COMPANY_LAT, COMPANY_LNG)
        employee = get_employee_by_line_id(line_id)

        if not employee:
            reply_message(reply_token, "❌ 請先綁定工號後再進行打卡！\n❌ Vui lòng gắn mã nhân viên trước khi chấm công!", channel_token)
            return

        now = datetime.now()
        hour = now.hour
        check_type = "上班" if hour < 15 else "下班"

        if has_checked_in_today(employee[0], check_type):
            reply_message(reply_token,
                f"❌ 您今天已打過【{check_type}】卡，請勿重複！\n❌ Bạn đã chấm công【{check_type}】hôm nay!",
                channel_token)
            return

        result = "成功" if distance <= ALLOWED_RADIUS_M else "失敗"
        save_checkin({
            "employee_id": employee[0],
            "name": employee[1],
            "line_id": line_id,
            "check_type": check_type,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": lat,
            "longitude": lng,
            "distance": round(distance, 2),
            "result": result
        })

        if result == "成功":
            reply_text = (
                f"✅ 打卡成功（{check_type}）！\n"
                f"🕒 時間：{now.strftime('%H:%M:%S')}\n"
                f"📍 距離公司：{round(distance)} 公尺\n"
                f"✅ Đã chấm công {check_type.lower()} thành công lúc {now.strftime('%H:%M:%S')}!"
            )
        else:
            reply_text = (
                f"❌ 超出公司定位範圍，打卡失敗！\n"
                f"📍 您距離公司約 {round(distance)} 公尺\n"
                f"❌ Không ở trong khu vực công ty, không thể chấm công!"
            )
        reply_message(reply_token, reply_text, channel_token)

# --- LINE 回覆 ---
def reply_message(reply_token, text, token):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "text",
            "text": text
        }]
    }
    requests.post(url, headers=headers, json=body)

# --- Haversine 距離計算 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

# --- 使用者綁定狀態資料 ---
def get_user_state(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT state, temp_employee_id FROM user_states WHERE line_id = ?", (line_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "temp_emp_id": row[1]}
    return None

def update_user_state(line_id, state, temp_emp_id=None):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO user_states (line_id, state, temp_employee_id, last_updated) VALUES (?, ?, ?, ?)",
                   (line_id, state, temp_emp_id, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def clear_user_state(line_id):
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_states WHERE line_id = ?", (line_id,))
    conn.commit()
    conn.close()
