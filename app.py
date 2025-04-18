from flask import Flask, request
from dotenv import load_dotenv
import os
import json
from line_utils import handle_event  # 假設 line_utils.py 內有處理 LINE 事件的邏輯

# 加載 .env 文件中的環境變數
load_dotenv()

# 讀取 LINE 的 channel secret 和 access token
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

# 初始化 Flask 應用
app = Flask(__name__)

# 回調 URL，用於接收 LINE 發送的 webhook 請求
@app.route("/callback", methods=["POST"])
def callback():
    # 獲取 LINE 服務器發送的 X-Signature 和請求體
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    # 呼叫處理事件的函數
    handle_event(body, signature, channel_secret, channel_token)
    return 'OK'

if __name__ == "__main__":
    # 啟動 Flask 服務
    app.run(debug=True)
