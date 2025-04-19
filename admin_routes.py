from flask import Blueprint, render_template, request, redirect, session, send_file
import sqlite3
import csv
import io
from datetime import datetime
import pytz

admin_bp = Blueprint("admin", __name__)
DB_PATH = 'checkin.db'

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
tz = pytz.timezone("Asia/Taipei")

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USERNAME and request.form["password"] == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin/dashboard")
        else:
            return render_template("admin_login.html", error="帳號或密碼錯誤")
    return render_template("admin_login.html")

@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/admin/login")

@admin_bp.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/admin/login")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, name, bind_time FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template("admin_dashboard.html", users=users)

@admin_bp.route("/delete_user/<employee_id>")
def delete_user(employee_id):
    if not session.get("admin"):
        return redirect("/admin/login")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE employee_id=?", (employee_id,))
    cursor.execute("DELETE FROM user_states WHERE temp_employee_id=?", (employee_id,))
    conn.commit()
    conn.close()
    return redirect("/admin/dashboard")

@admin_bp.route("/export_checkins", methods=["POST"])
def export_checkins_csv():
    if not session.get("admin"):
        return redirect("/admin/login")

    daterange = request.form["daterange"]
    try:
        start_date, end_date = [s.strip() for s in daterange.split("-")]
    except Exception:
        return "日期格式錯誤，請輸入格式如 2025-04-01 - 2025-04-19", 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT employee_id, name, timestamp, check_type, result
        FROM checkins
        WHERE DATE(timestamp) BETWEEN ? AND ?
        ORDER BY employee_id, timestamp
    """, (start_date, end_date))
    records = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工號", "姓名", "日期", "時間", "類型", "狀態"])

    for emp_id, name, ts, check_type, result in records:
        # 時區轉換
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        local_ts = ts_dt.replace(tzinfo=pytz.utc).astimezone(tz)
        writer.writerow([emp_id, name, local_ts.date(), local_ts.strftime("%H:%M"), check_type, result])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f"打卡紀錄_{start_date}_to_{end_date}.csv")

@admin_bp.route("/export_locations", methods=["POST"])
def export_location_logs_csv():
    if not session.get("admin"):
        return redirect("/admin/login")

    daterange = request.form["daterange"]
    try:
        start_date, end_date = [s.strip() for s in daterange.split("-")]
    except Exception:
        return "日期格式錯誤，請輸入格式如 2025-04-01 - 2025-04-19", 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT employee_id, name, timestamp, latitude, longitude
        FROM location_logs
        WHERE DATE(timestamp) BETWEEN ? AND ?
        ORDER BY employee_id, timestamp
    """, (start_date, end_date))
    records = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工號", "姓名", "日期", "時間", "緯度", "經度"])

    for emp_id, name, ts, lat, lng in records:
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        local_ts = ts_dt.replace(tzinfo=pytz.utc).astimezone(tz)
        writer.writerow([emp_id, name, local_ts.date(), local_ts.strftime("%H:%M"), lat, lng])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f"定位紀錄_{start_date}_to_{end_date}.csv")
