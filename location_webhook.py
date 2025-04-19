from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime
import pytz

location_bp = Blueprint("location", __name__)
DB_PATH = 'checkin.db'
tz = pytz.timezone("Asia/Taipei")

@location_bp.route("/webhook", methods=["POST"])
def receive_location():
    try:
        data = request.get_json()
        print("📥 OwnTracks 資料：", data)

        # 提取座標
        latitude = float(data.get("lat"))
        longitude = float(data.get("lon"))
        topic = data.get("topic", "")

        # 解析 topic：owntracks/{employee_id}/device
        parts = topic.split("/")
        if len(parts) < 2:
            return jsonify({"status": "error", "message": "無效的 topic 格式"}), 400

        employee_id = parts[1]  # 工號來自 topic 第二段

        # 時間處理
        if "tst" in data:
            utc_time = datetime.utcfromtimestamp(data["tst"]).replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(tz)
        else:
            local_time = datetime.now(tz)

        timestamp_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 查詢對應的 LINE 使用者
        cursor.execute("SELECT line_id, name FROM users WHERE employee_id = ?", (employee_id,))
        user_row = cursor.fetchone()

        if user_row:
            line_id, name = user_row
        else:
            return jsonify({"status": "error", "message": "尚未綁定該工號，無法記錄"}), 403

        # 寫入定位資料
        cursor.execute('''
            INSERT INTO location_logs (line_id, employee_id, name, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (line_id, employee_id, name, latitude, longitude, timestamp_str))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "✅ 定位已成功記錄"})

    except Exception as e:
        print("🚨 Webhook 錯誤：", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
