from flask import Flask, request, jsonify
from line_utils import handle_event
from db import init_db  # 初始化資料庫
import os
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

app = Flask(__name__)

# 環境變數
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 初始化 SQLite 資料庫（建表）
init_db()

@app.route("/line/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handle_event(body, signature, CHANNEL_SECRET, CHANNEL_ACCESS_TOKEN)
    except Exception as e:
        print(f"Webhook Error: {e}")
        return "Error", 500
    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)