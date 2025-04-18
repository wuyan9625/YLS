from flask import Flask, request
from dotenv import load_dotenv
import os
from line_utils import handle_event  # 引入 line_utils.py

# 加載 .env 文件中的環境變數
load_dotenv()

# 讀取 LINE 的 channel secret 和 access token
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

# 初始化 Flask 應用
app = Flask(__name__)

@app.route("/line/webhook", methods=["POST"])
def callback():
    # 獲取 LINE 服務器發送的 X-Signature 和請求體
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    # 呼叫處理事件的函數
    handle_event(body, signature, channel_secret, channel_token)
    return 'OK'

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)