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

        # 安全提取經緯度（支援 lat/lon 或 latitude/longitude）
        lat_raw = data.get("lat") or data.get("latitude")
        lon_raw = data.get("lon") or data.get("longitude")
        if lat_raw is None or lon_raw is None:
            return jsonify({"status": "error", "message": "缺少定位資料"}), 400

        latitude = float(lat_raw)
        longitude = float(lon_raw)

        # 解析 topic
        topic = data.get("topic", "")
        parts = topic.split("/")
        if len(parts) < 2:
            return jsonify({"status": "error", "message": "無效的 topic 格式"}), 400

        employee_id = parts[1]  # owntracks/{employee_id}/device

        # 處理時間
        if "tst" in data:
            utc_time = datetime.utcfromtimestamp(data["tst"]).replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(tz)
        else:
            local_time = datetime.now(tz)
        timestamp_str = local_time.strftime("%Y-%m-%d %H:%M:%S")

        # 查詢對應 user
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT line_id, name FROM users WHERE employee_id = ?", (employee_id,))
        user_row = cursor.fetchone()

        if not user_row:
            return jsonify({"status": "error", "message": "尚未綁定該工號，無法記錄"}), 403

        line_id, name = user_row

        # 寫入資料
        cursor.execute('''
            INSERT INTO location_logs (line_id, employee_id, name, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (line_id, employee_id, name, latitude, longitude, timestamp_str))

        conn.commit()
        conn.close()

        print(f"✅ 定位儲存成功：{employee_id} - {latitude}, {longitude}")
        return jsonify({"status": "success", "message": "✅ 定位已成功記錄"})

    except Exception as e:
        print("🚨 Webhook 錯誤：", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500
