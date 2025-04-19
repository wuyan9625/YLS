from flask import Blueprint, render_template, request, redirect, session, send_file
import sqlite3
import csv
import io
from datetime import datetime
import pytz

admin_bp = Blueprint("admin", __name__)
DB_PATH = 'checkin.db'
tz = pytz.timezone("Asia/Taipei")

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

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

    # 員工資料
    cursor.execute("SELECT employee_id, name, bind_time FROM users")
    users = cursor.fetchall()

    # 打卡可選日期（yyyy-mm-dd）
    cursor.execute("SELECT DISTINCT DATE(timestamp) FROM checkins ORDER BY timestamp DESC")
    checkin_dates = [r[0] for r in cursor.fetchall()]

    # 定位可選日期
    cursor.execute("SELECT DISTINCT DATE(timestamp) FROM location_logs ORDER BY timestamp DESC")
    location_dates = [r[0] for r in cursor.fetchall()]

    # 額外生成月份列表（yyyy-mm）
    checkin_months = sorted({d[:7] for d in checkin_dates}, reverse=True)
    location_months = sorted({d[:7] for d in location_dates}, reverse=True)

    conn.close()
    return render_template("admin_dashboard.html",
                           users=users,
                           checkin_dates=checkin_dates,
                           location_dates=location_dates,
                           checkin_months=checkin_months,
                           location_months=location_months)

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

    daterange = request.form.get("daterange") or ""
    if " - " in daterange:
        start_date, end_date = [d.strip() for d in daterange.split(" - ")]
    elif len(daterange) == 7:  # yyyy-mm
        start_date = f"{daterange}-01"
        end_date = f"{daterange}-31"
    else:
        return "無效的日期格式", 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, name, timestamp, check_type, result
        FROM checkins
        WHERE DATE(timestamp) BETWEEN ? AND ?
        ORDER BY employee_id, timestamp
    ''', (start_date, end_date))
    records = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工號", "姓名", "日期", "時間", "類型", "狀態"])

    for emp_id, name, ts, ctype, result in records:
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        local_ts = tz.localize(ts_dt)  # ✅ 正確處理台灣時間
        writer.writerow([emp_id, name, local_ts.date(), local_ts.strftime("%H:%M"), ctype, result])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f"打卡紀錄_{start_date}_to_{end_date}.csv")

@admin_bp.route("/export_locations", methods=["POST"])
def export_location_logs_csv():
    if not session.get("admin"):
        return redirect("/admin/login")

    daterange = request.form.get("daterange") or ""
    if " - " in daterange:
        start_date, end_date = [d.strip() for d in daterange.split(" - ")]
    elif len(daterange) == 7:  # yyyy-mm
        start_date = f"{daterange}-01"
        end_date = f"{daterange}-31"
    else:
        return "無效的日期格式", 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT employee_id, name, timestamp, latitude, longitude
        FROM location_logs
        WHERE DATE(timestamp) BETWEEN ? AND ?
        ORDER BY employee_id, timestamp
    ''', (start_date, end_date))
    records = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工號", "姓名", "日期", "時間", "緯度", "經度"])

    for emp_id, name, ts, lat, lng in records:
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        local_ts = tz.localize(ts_dt)
        writer.writerow([emp_id, name, local_ts.date(), local_ts.strftime("%H:%M"), lat, lng])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name=f"定位紀錄_{start_date}_to_{end_date}.csv")
