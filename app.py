from flask import Flask, request
from line_utils import handle_event
from db import init_db, export_checkins_csv
from dotenv import load_dotenv
import os
import json

load_dotenv()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    return "✅ LINE 打卡系統已啟動"

@app.route("/line/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handle_event(json.loads(body), signature, CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN)
    except Exception as e:
        print("Webhook Error:", e)
        return "Error", 400
    return "OK", 200

@app.route("/export/csv", methods=["GET"])
def export_csv():
    month = request.args.get("month")  # 例如：2025-03
    csv_data = export_checkins_csv(month)
    filename = f"checkin_report_{month or 'current'}.csv"
    return (
        csv_data,
        200,
        {
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
