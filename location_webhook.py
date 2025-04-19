from flask import Blueprint, request, jsonify
import sqlite3
from datetime import datetime

location_bp = Blueprint("location", __name__)
DB_PATH = 'checkin.db'

@location_bp.route("/webhook", methods=["POST"])
def receive_location():
    try:
        data = request.get_json()
        line_id = data.get("line_id")
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
        timestamp = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT employee_id, name FROM users WHERE line_id=?", (line_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "找不到綁定的用戶"}), 404

        employee_id, name = row

        cursor.execute('''
            INSERT INTO location_logs (line_id, employee_id, name, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (line_id, employee_id, name, latitude, longitude, timestamp))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "定位已記錄"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
