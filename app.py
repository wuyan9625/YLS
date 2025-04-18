from flask import Flask, request
from db import init_db, bind_user, save_checkin, has_checked_in_today, get_employee_by_line_id
from line_utils import handle_event
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 初始化資料庫
init_db()

@app.route("/line/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    events = body.get("events", [])
    for event in events:
        handle_event(event, CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN)
    return "OK", 200

@app.route("/")
def index():
    return "LINE 打卡後端運作中！"

if __name__ == "__main__":
    app.run(port=5000)