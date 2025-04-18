from flask import Flask, request
from line_utils import handle_event

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    channel_secret = "your_channel_secret"
    channel_token = "your_channel_token"
    
    handle_event(body, signature, channel_secret, channel_token)
    return 'OK'

if __name__ == "__main__":
    app.run(debug=True)
