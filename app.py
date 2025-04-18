from flask import Flask, request
from line_utils import handle_event
from db import init_db, export_checkins_csv
from dotenv import load_dotenv
import os

# 載入 .env 中的 LINE 金鑰
load_dotenv()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

app = Flask(__name__)

# 初始化資料庫（第一次自動建立）
init_db()

@app.route("/")
def index():
    return "✅ LINE Bot 打卡系統運行中"

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
