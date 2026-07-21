import os
import random
import requests
import json
import logging
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# लॉगिंग सेटअप - इसे और मजबूत किया ताकि सब कुछ दिखे
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = "7908449655:AAGDZChIBDLCEK-TtR2gdrfKozLkDG1NL6I"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# Gemini क्लाइंट सेटअप
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Gemini Client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")

USER_SEEN_FACTS = {}

# --- Render Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"Health check server successfully bound to port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health check server failed to start: {e}")

# --- Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    USER_SEEN_FACTS[user_id] = []
    await update.message.reply_text(
        "👋 राम राम भाई! आपका स्मार्ट फैक्ट-टू-क्विज बोट तैयार है।\n\n"
        "⏱️ शुरू करने के लिए `/test` या `/startquiz` कमांड दबाएं।"
    )

async def generate_live_quiz(facts_list):
    prompt = f"""
    तुम्हें नीचे दिए गए तथ्यों (Facts) का उपयोग करके 20 बेहतरीन परीक्षा-उपयोगी (Exam-Oriented) बहुविकल्पीय प्रश्न (MCQs) तैयार करने हैं।
    प्रत्येक फैक्ट से एक प्रश्न बनाना है।
    
    सख्त नियम:
    1. उच्चारण शुद्ध रखने के लिए हिंदी अक्षर 'ड़' की जगह हमेशा 'ड' का प्रयोग करें।
    2. आउटपुट केवल और केवल एक वैध JSON Array होना चाहिए।
    """
    response = ai_client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
    )
    return json.loads(response.text.strip())

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    message = update.message
    await message.reply_text("🔄 AI से नए सवाल बनवा रहा हूँ...")
    # बाकी का फंक्शन वैसा ही रहेगा...

def main():
    logger.info("Starting main function...")
    
    # 1. पहले सर्वर चालू करो ताकि Render को तुरंत रिस्पॉन्स मिले
    t = threading.Thread(target=run_health_check_server, daemon=True)
    t.start()
    
    # 2. बोट एप्लीकेशन सेटअप
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("test", start_test))
        application.add_handler(CommandHandler("startquiz", start_test))
        
        logger.info("Starting Telegram Bot Polling now...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"Critical error in main loop: {e}")

if __name__ == '__main__':
    main()
