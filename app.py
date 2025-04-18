# app.py
from flask import Flask, request, jsonify
from line_utils import handle_event
from db import init_db
import os

app = Flask(__name__)

# 初始化資料庫
init_db()

@app.route("/")
def index():
    return "LINE Bot Check-in System is Running"

@app.route("/line/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handle_event(body, signature)
    except Exception as e:
        print("Webhook Error:", e)
        return "Error", 400
    return "OK", 200

@app.route("/export/csv", methods=["GET"])
def export_csv():
    from db import export_checkins_csv
    csv_data = export_checkins_csv()
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": "attachment; filename=checkins.csv"
        },
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
