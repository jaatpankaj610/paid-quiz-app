import os
import json
import logging
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# लॉगिंग सेटअप
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# क्रेडेंशियल्स (Render Environment Variables से लेना सबसे सुरक्षित है)
# अगर आप अभी कोड में डालना चाहते हैं तो यहाँ डालें, लेकिन बाद में बदल लें
TELEGRAM_BOT_TOKEN = "7908449655:AAGDZChIBDLCEK-TtR2gdrfKozLkDG1NL6I"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# Gemini क्लाइंट सेटअप
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini Client initialized.")
except Exception as e:
    logger.error(f"Gemini Client error: {e}")

# --- Health Check Server (Render के लिए ज़रूरी) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server on port {port}")
    server.serve_forever()

# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 राम राम भाई! बोट चालू है। क्विज़ के लिए /test लिखें।")

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 AI सवाल तैयार कर रहा है, कृपया प्रतीक्षा करें...")

def main():
    # 1. हेल्थ चेक सर्वर शुरू करें
    t = threading.Thread(target=run_health_check_server, daemon=True)
    t.start()
    
    # 2. बोट शुरू करें
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("test", start_test))
        
        logger.info("Bot is starting polling...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
