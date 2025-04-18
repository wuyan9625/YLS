import sqlite3
import requests
import json
from datetime import datetime

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
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()  # 如果狀態碼不是 2xx，將拋出異常
        print(response.json())  # 打印回應檢查是否正確
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
        # 可以發送錯誤通知給管理員或記錄錯誤

# --- LINE webhook 入口 ---
def handle_event(body, signature, channel_secret, channel_token):
    body_json = json.loads(body)
    events = body_json.get("events", [])
    for event in events:
        process_event(event, channel_token)

# --- 單筆事件處理邏輯 ---
def process_event(event, channel_token):
    from db import bind_user, get_employee_by_line_id, is_employee_id_taken  # 延遲導入，避免循環依賴

    event_type = event.get("type")
    reply_token = event.get("replyToken")
    message = event.get("message", {})
    line_id = event.get("source", {}).get("userId")

    # 處理用戶消息
    if event_type == "message" and message.get("type") == "text":
        text = message.get("text").strip()

        # 處理綁定邏輯
        if text in ["綁定", "我要綁定", "gắn mã", "gắn", "bind"]:
            update_user_state(line_id, "WAIT_EMP_ID")
            reply_message(reply_token, "📋 請輸入您的工號", channel_token)  # 中文
            reply_message(reply_token, "📋 Vui lòng nhập mã nhân viên của bạn", channel_token)  # 越南文
            return

        # 處理綁定狀態
        state_info = get_user_state(line_id)
        if state_info:
            state = state_info["state"]
            if state == "WAIT_EMP_ID":
                emp_id = text
                if is_employee_id_taken(emp_id):
                    reply_message(reply_token, "❌ 此工號已被綁定！", channel_token)  # 中文
                    reply_message(reply_token, "❌ Mã nhân viên này đã được sử dụng!", channel_token)  # 越南文
                    return
                update_user_state(line_id, "WAIT_NAME", temp_emp_id=emp_id)
                reply_message(reply_token, "📋 請輸入您的姓名", channel_token)  # 中文
                reply_message(reply_token, "📋 Vui lòng nhập tên của bạn", channel_token)  # 越南文
                return
            elif state == "WAIT_NAME":
                emp_id = state_info["temp_emp_id"]
                name = text
                if bind_user(line_id, emp_id, name):
                    reply_message(reply_token,
                        f"✅ 綁定成功！工號：{emp_id}，姓名：{name}", channel_token)  # 中文
                    reply_message(reply_token,
                        f"✅ Gắn mã thành công! Mã nhân viên: {emp_id}, Tên: {name}", channel_token)  # 越南文
                else:
                    reply_message(reply_token, "❌ 綁定失敗，請重試", channel_token)  # 中文
                    reply_message(reply_token, "❌ Gắn mã thất bại, vui lòng thử lại", channel_token)  # 越南文
                clear_user_state(line_id)
                return

        # 打卡邏輯：如果沒綁定工號則不能打卡
        if text in ["上班", "下班"]:
            employee = get_employee_by_line_id(line_id)
            if not employee:
                reply_message(reply_token, "❌ 請先綁定工號再打卡", channel_token)  # 中文
                reply_message(reply_token, "❌ Vui lòng gắn mã trước khi chấm công", channel_token)  # 越南文
                return

            check_type = "上班" if text == "上班" else "下班"
            now = datetime.now()
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

            # 顯示上班或下班時間
            if check_type == "上班":
                if has_checked_in_today(employee[0], "上班"):
                    reply_message(reply_token, 
                        "❌ 您今天已經上班過了，無法再次上班！ / ❌ Bạn đã chấm công rồi. Không thể chấm công nhiều lần.", channel_token)  # 中文 + 越南文
                    return
                if has_checked_in_today(employee[0], "下班"):
                    reply_message(reply_token, 
                        "❌ 您今天已經下班，無法再上班！ / ❌ Bạn đã tan ca, không thể chấm công lên lại.", channel_token)  # 中文 + 越南文
                    return
                save_checkin({
                    "employee_id": employee[0],
                    "line_id": line_id,
                    "name": employee[1],
                    "check_type": "上班",
                    "timestamp": formatted_time,
                    "result": "成功"
                })
                reply_message(reply_token, 
                    f"✅ 上班打卡成功！\n上班時間：{formatted_time} / ✅ Đăng ký thành công\nGiờ chấm công vào: {formatted_time}",
                    channel_token)  # 中文 + 越南文

            if check_type == "下班":
                if not has_checked_in_today(employee[0], "上班"):
                    reply_message(reply_token, 
                        "❌ 您未上班，無法下班！ / ❌ Bạn chưa chấm công lên, không thể chấm công xuống.", channel_token)  # 中文 + 越南文
                    return
                save_checkin({
                    "employee_id": employee[0],
                    "line_id": line_id,
                    "name": employee[1],
                    "check_type": "下班",
                    "timestamp": formatted_time,
                    "result": "成功"
                })
                reply_message(reply_token, 
                    f"✅ 下班打卡成功！\n下班時間：{formatted_time} / ✅ Đã chấm công thành công\nGiờ chấm công ra: {formatted_time}",
                    channel_token)  # 中文 + 越南文

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
