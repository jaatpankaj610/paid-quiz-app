import os
import sys
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# 1. बेहतर लॉगिंग
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = "7908449655:AAGDZChIBDLCEK-TtR2gdrfKozLkDG1NL6I"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# 3. Gemini सेटअप
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini Client Ready!")
except Exception as e:
    logger.error(f"❌ Gemini Error: {e}")

# 4. Render Health Check Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 10000)) # Render uses 10000 or $PORT
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🚀 Health Server live on port {port}")
    httpd.serve_forever()

# 5. Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 राम राम भाई! बोट अब स्थिर (Stable) है।")

# 6. मैन्युअल बोट रनर (Updater Bug से बचने के लिए)
async def run_bot():
    # Application बनाना
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # कमांड्स जोड़ना
    application.add_handler(CommandHandler("start", start))
    
    # बोट को शुरू करना
    async with application:
        await application.initialize()
        await application.start()
        logger.info("🤖 Bot Started and Waiting for Messages...")
        # Polling शुरू करना (Updater bug से बचने का सबसे सुरक्षित तरीका)
        await application.updater.start_polling(drop_pending_updates=True)
        
        # बोट को चलता रखने के लिए (Infinite Loop)
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    # हेल्थ सर्वर को थ्रेड में चलाएँ
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # बोट को चलाएँ
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"💥 Bot Crash: {e}")
        sys.exit(1)
