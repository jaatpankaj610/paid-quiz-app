import os
import sys
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 1. लॉगिंग सेटअप (ताकि Render पर सब दिखे)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स (इसे यहाँ सीधे डाल रहा हूँ जैसा आपने कहा)
TELEGRAM_BOT_TOKEN = "7908449655:AAGDZChIBDLCEK-TtR2gdrfKozLkDG1NL6I"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# 3. Gemini क्लाइंट (Try-Except के साथ ताकि क्रैश न हो)
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini Client initialized successfully!")
except Exception as e:
    logger.error(f"❌ Gemini Error: {e}")

# 4. Health Check Server (Render की फ्री सर्विस के लिए बहुत ज़रूरी)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is live!")
    def log_message(self, format, *args): return # फालतू लॉग्स रोकने के लिए

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    # '0.0.0.0' पर बाइंड करना ज़रूरी है
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🚀 Health Server running on port {port}")
    httpd.serve_forever()

# 5. बोट कमांड्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 राम राम भाई! बोट एकदम फिट है।")

# 6. मुख्य फंक्शन
def main():
    # पहले सर्वर चालू करो ताकि Render को लगे कि ऐप 'Live' है
    server_thread = threading.Thread(target=run_health_check, daemon=True)
    server_thread.start()
    
    # 2 सेकंड का इंतज़ार ताकि सर्वर सेटल हो जाए
    time.sleep(2)

    try:
        logger.info("🤖 Starting Telegram Bot...")
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        
        # 'drop_pending_updates' पुराने मैसेज इग्नोर करने के लिए
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"💥 Bot Polling Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
