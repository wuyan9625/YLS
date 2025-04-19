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
        line_id = data.get("line_id")
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))

        # 嘗試取得 timestamp，若有傳入則解析為台灣時間，否則使用現在時間
        if "timestamp" in data:
            try:
                utc_time = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                local_time = utc_time.astimezone(tz)
            except:
                local_time = datetime.now(tz)
        else:
            local_time = datetime.now(tz)

        timestamp_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 查詢綁定使用者
        cursor.execute("SELECT employee_id, name FROM users WHERE line_id=?", (line_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "找不到綁定的用戶"}), 404

        employee_id, name = row

        # 寫入定位紀錄
        cursor.execute('''
            INSERT INTO location_logs (line_id, employee_id, name, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (line_id, employee_id, name, latitude, longitude, timestamp_str))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "定位已記錄"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
