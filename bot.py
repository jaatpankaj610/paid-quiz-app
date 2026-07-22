import os
import sys
import logging
import threading
import asyncio
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# 3. हेल्थ सर्वर (Render के लिए)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Quiz Bot is Online")
    def log_message(self, format, *args): return

def run_health_server():
    httpd = HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

# --- 4. AI QUIZ GENERATION ---

def load_user_facts():
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return "\n".join(data) if isinstance(data, list) else str(data)
    except: pass
    return "भारत का इतिहास और सामान्य ज्ञान।"

async def generate_20_questions():
    user_facts = load_user_facts()
    
    # Prompt for 20 questions
    prompt = f"""
    तुम्हें नीचे दिए गए तथ्यों (Facts) का उपयोग करके 20 बेहतरीन GK MCQs तैयार करने हैं।
    तथ्य: {user_facts}
    
    नियम:
    1. 'ड़' की जगह हमेशा 'ड' का प्रयोग करें।
    2. आउटपुट केवल एक शुद्ध JSON Array होना चाहिए।
    Format: [{{ "question": "...", "options": ["A", "B", "C", "D"], "answer": 0 }}]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return None

# --- 5. BOT HANDLERS ---

# Global lock to ignore other commands
is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    if is_bot_busy:
        return # Ignore if already processing

    is_bot_busy = True
    status_msg = await update.message.reply_text("🚀 AI 20 सवाल तैयार कर रहा है... कृपया प्रतीक्षा करें। अब कोई और कमांड काम नहीं करेगी।")

    quiz_data = await generate_20_questions()

    if not quiz_data:
        await status_msg.edit_text("❌ माफ़ी चाहता हूँ, AI सवाल नहीं बना पाया। कृपया थोड़ी देर बाद /start करें।")
        is_bot_busy = False
        return

    # Prepare the big message with all 20 questions
    full_quiz_text = "📝 **GK QUIZ - 20 QUESTIONS** 📝\n\n"
    
    for i, q in enumerate(quiz_data, 1):
        full_quiz_text += f"❓ **सवाल {i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            full_quiz_text += f"   {opts[idx]}) {opt}\n"
        
        # Adding correct answer hiddenly or at the end (Optional)
        correct_opt = opts[q['answer']]
        full_quiz_text += f"✅ **उत्तर:** {correct_opt}\n\n"

        # Telegram message limit check (4096 chars)
        if len(full_quiz_text) > 3500:
            await update.message.reply_text(full_quiz_text, parse_mode='Markdown')
            full_quiz_text = ""

    if full_quiz_text:
        await update.message.reply_text(full_quiz_text, parse_mode='Markdown')

    # Final Screen
    await update.message.reply_text("🏆 **टेस्ट पूरा हुआ!**\n\nसभी 20 सवाल ऊपर दिए गए हैं। अब आप दोबारा /start कर सकते हैं।")
    
    is_bot_busy = False # Unlock the bot

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """This function catches all other messages when the bot is busy."""
    global is_bot_busy
    if is_bot_busy:
        # Don't do anything, just ignore
        return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    
    # Catch all other messages/commands and ignore them
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(run_bot())
    except: sys.exit(1)
