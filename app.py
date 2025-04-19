from flask import Flask
from dotenv import load_dotenv
from db import init_db
from line_utils import handle_event
from location_webhook import location_bp
from admin_routes import admin_bp
import os
from flask import request, abort

# 載入 .env 設定
load_dotenv()

# ✅ 確保 static/qr 資料夾存在
os.makedirs("static/qr", exist_ok=True)

# 初始化資料庫
init_db()

# 建立 Flask App
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# LINE Webhook
@app.route("/callback", methods=["POST"])
def callback():
    try:
        body = request.get_data(as_text=True)
        handle_event(body)
        return "OK"
    except Exception as e:
        print("LINE webhook 處理失敗：", str(e))
        abort(400)

# Blueprint 路由
app.register_blueprint(location_bp, url_prefix="/location")
app.register_blueprint(admin_bp, url_prefix="/admin")

if __name__ == "__main__":
    app.run()
