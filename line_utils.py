import sqlite3
import requests
import json
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from db import (
    bind_user, get_employee_by_line_id, is_employee_id_taken,
    is_line_id_bound, has_checked_in_today, save_checkin
)

# --- 計算距離（Haversine公式）---
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * asin(sqrt(a))

# --- 回傳文字訊息 ---
def reply_message(reply_token, text, token):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=body)
    print(response.json())  # 打印回應檢查是否正確

# --- 回傳按鈕模板訊息（中越文）---
def reply_button_template(reply_token, token):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{
            "type": "template",
            "altText": "點選操作",
            "template": {
                "type": "buttons",
                "title": "🔧 功能選單 / Menu chức năng",
                "text": "請選擇操作（Vui lòng chọn thao tác）",
                "actions": [
                    {"type": "message", "label": "綁定 / Gắn mã", "text": "綁定"},
                    {"type": "message", "label": "上班 / Đi làm", "text": "上班"},
                    {"type": "message", "label": "下班 / Tan ca", "text": "下班"}
                ]
            }
        }]
    }
    response = requests.post(url, headers=headers, json=body)
    print(response.json())  # 打印回應檢查是否正確

# --- LINE webhook 入口 ---
def handle_event(body, signature, channel_secret, channel_token):
    body_json = json.loads(body)
    events = body_json.get("events", [])
    for event in events:
        process_event(event, channel_token)

# --- 單筆事件處理邏輯 ---
def process_event(event, channel_token):
    event_type = event.get("type")
    reply_token = event.get("replyToken")
    message = event.get("message", {})
    line_id = event.get("source", {}).get("userId")

    # 加入好友後自動發送歡迎文字與按鈕
    if event_type == "follow":
        welcome_text = (
            "👋 歡迎加入打卡系統！\n\n"
            "📋 請依照下列指引開始：\n"
            "🔹 輸入「綁定」開始工號註冊\n"
            "🔹 輸入「上班」或「下班」進行打卡\n"
            "\n📱 安裝定位 App（Android/iOS）：\n"
            "https://owntracks.org/booklet/guide/installation/\n"
            "（開啟定位、自動上傳）\n\n"
            "👋 Chào mừng bạn đến hệ thống chấm công!\n"
            "🔹 Gõ “gắn mã” để bắt đầu đăng ký\n"
            "🔹 Gõ “上班” hoặc “下班” để chấm công\n"
            "📍 Vui lòng cài App định vị và bật nền"
        )
        reply_message(reply_token, welcome_text, channel_token)
        reply_button_template(reply_token, channel_token)  # 顯示按鈕選單
        return

    if event_type == "message" and message.get("type") == "text":
        text = message.get("text").strip()

        if text in ["綁定", "我要綁定", "gắn mã", "gắn", "bind"]:
            update_user_state(line_id, "WAIT_EMP_ID")
            reply_message(reply_token, "📋 請輸入您的工號（mã nhân viên）", channel_token)
            return

        # 處理綁定狀態
        state_info = get_user_state(line_id)
        if state_info:
            state = state_info["state"]
            if state == "WAIT_EMP_ID":
                emp_id = text
                if is_employee_id_taken(emp_id):
                    reply_message(reply_token, "❌ 此工號已被綁定！\n❌ Mã nhân viên đã được sử dụng!", channel_token)
                    return
                update_user_state(line_id, "WAIT_NAME", temp_emp_id=emp_id)
                reply_message(reply_token, "📋 請輸入您的姓名（tên）", channel_token)
                return
            elif state == "WAIT_NAME":
                emp_id = state_info["temp_emp_id"]
                name = text
                if bind_user(line_id, emp_id, name):
                    reply_message(reply_token,
                        f"✅ 綁定成功！工號：{emp_id}，姓名：{name}\n"
                        f"✅ Đã gắn mã nhân viên: {emp_id}, tên: {name}",
                        channel_token)
                else:
                    reply_message(reply_token, "❌ 綁定失敗，請重試\n❌ Không thể gắn mã", channel_token)
                clear_user_state(line_id)
                return

        if text in ["上班", "下班"]:
            # 檢查是否已打過上班卡
            employee = get_employee_by_line_id(line_id)
            if not employee:
                reply_message(reply_token, "❌ 請先綁定工號再打卡\n❌ Vui lòng gắn mã trước khi chấm công", channel_token)
                return

            check_type = "上班" if text == "上班" else "下班"
            now = datetime.now()

            # 檢查是否已經打過上班卡
            if check_type == "上班":
                if has_checked_in_today(employee[0], "上班"):
                    reply_message(reply_token, "❌ 您今天已經上班過了，無法再次上班！", channel_token)
                    return
                if has_checked_in_today(employee[0], "下班"):
                    reply_message(reply_token, "❌ 您今天已經下班，無法再上班！", channel_token)
                    return
                # 記錄上班時間
                save_checkin({
                    "employee_id": employee[0],
                    "line_id": line_id,
                    "name": employee[1],
                    "check_type": "上班",
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "result": "成功"
                })
                reply_message(reply_token, f"✅ 上班打卡成功！", channel_token)

            # 檢查是否已經打過下班卡
            if check_type == "下班":
                if not has_checked_in_today(employee[0], "上班"):
                    reply_message(reply_token, "❌ 您未上班，無法下班！", channel_token)
                    return
                save_checkin({
                    "employee_id": employee[0],
                    "line_id": line_id,
                    "name": employee[1],
                    "check_type": "下班",
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "result": "成功"
                })
                reply_message(reply_token, f"✅ 下班打卡成功！", channel_token)

# --- 暫存綁定狀態 ---
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