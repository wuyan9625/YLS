from flask import Flask, request, render_template, redirect, session, url_for, jsonify
from line_utils import handle_event
from db import (
    init_db, get_employee_by_line_id, has_checked_in_today, save_checkin,
    save_location_log, export_checkins_summary_csv, export_location_logs_csv
)
from line_utils import calculate_distance
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3

# === 初始化 Flask 與環境變數 ===
load_dotenv()
app = Flask(__name__)
app.secret_key = "super_secret_key"
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

COMPANY_LAT = 24.4804401433383
COMPANY_LNG = 120.7956030766374
ALLOWED_RADIUS_M = 50

# === 初始化資料庫 ===
init_db()

# --- LINE webhook ---
@app.route("/")
def index():
    return "LINE Bot Check-in System is Running"

@app.route("/line/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        print("🟡 收到 webhook：", body)
        handle_event(body, signature, CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN)
    except Exception as e:
        print("🔴 Webhook Error:", e)
        return "Error", 400
    return "OK", 200

# --- OwnTracks 定位 webhook ---
@app.route("/location/webhook", methods=["POST"])
def location_webhook():
    data = request.json
    if data.get("_type") != "location":
        return jsonify({"error": "非位置資料"}), 400

    tid = data.get("tid")
    lat = data.get("lat")
    lng = data.get("lon")
    timestamp = datetime.fromtimestamp(data.get("tst")).strftime("%Y-%m-%d %H:%M:%S")
    hour = datetime.fromtimestamp(data.get("tst")).hour

    employee = get_employee_by_line_id(tid)
    if not employee:
        return jsonify({"error": "使用者未綁定"}), 400

    distance = calculate_distance(lat, lng, COMPANY_LAT, COMPANY_LNG)
    save_location_log(employee[0], employee[1], tid, lat, lng, timestamp, distance)

    if distance > ALLOWED_RADIUS_M:
        return jsonify({"status": "位置太遠"}), 200

    check_type = "上班" if hour < 15 else "下班"
    if has_checked_in_today(employee[0], check_type):
        return jsonify({"status": "已打卡過"}), 200

    save_checkin({
        "employee_id": employee[0],
        "line_id": tid,
        "name": employee[1],
        "check_type": check_type,
        "timestamp": timestamp,
        "result": "自動打卡"
    })
    return jsonify({"status": "打卡成功"}), 200

# === 管理員系統 ===
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin/dashboard")
        return render_template("admin_login.html", error="帳號或密碼錯誤")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, name, bind_time FROM users ORDER BY bind_time DESC")
    users = [{"employee_id": r[0], "name": r[1], "bind_time": r[2]} for r in cursor.fetchall()]
    conn.close()
    return render_template("admin_dashboard.html", users=users)

@app.route("/admin/delete_user", methods=["POST"])
def admin_delete_user():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")
    employee_id = request.form.get("employee_id")
    conn = sqlite3.connect("checkin.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE employee_id = ?", (employee_id,))
    conn.commit()
    conn.close()
    return redirect("/admin/dashboard")

@app.route("/admin/export/checkins")
def admin_export_checkins():
    if request.args.get("user") != ADMIN_USERNAME or request.args.get("pass") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    csv_data = export_checkins_summary_csv()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=checkins_summary.csv"
        }
    )

@app.route("/admin/export/location_logs")
def admin_export_location_logs():
    if request.args.get("user") != ADMIN_USERNAME or request.args.get("pass") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    csv_data = export_location_logs_csv()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=location_logs.csv"
        }
    )

# === 啟動應用 ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
