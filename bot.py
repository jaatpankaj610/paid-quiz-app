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

# 1. Logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 2. Credentials
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# 3. Health Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Quiz Bot is Online")
    def log_message(self, format, *args): return

def run_health_server():
    httpd = HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

# --- 4. AI QUIZ GENERATION (BATCH METHOD) ---

def load_user_facts():
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return "\n".join(data) if isinstance(data, list) else str(data)
    except: pass
    return "भारत का इतिहास, भूगोल और सामान्य ज्ञान।"

async def fetch_questions_from_ai(count=10):
    """AI se sawal mangne ka ek chota function"""
    user_facts = load_user_facts()
    prompt = f"""
    Generate {count} GK MCQs in Hindi based on: {user_facts}.
    Strictly follow:
    1. Output ONLY a valid JSON array.
    2. Use 'ड' instead of 'ड़'.
    3. Format: [{{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}}]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        logger.error(f"Batch Error: {e}")
    return []

# --- 5. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    if is_bot_busy:
        return # Do nothing if already working

    is_bot_busy = True
    status_msg = await update.message.reply_text("⏳ AI 20 सवाल तैयार कर रहा है (Batch 1/2)...")

    # Batch 1: Pehle 10 sawal
    batch1 = await fetch_questions_from_ai(10)
    
    await status_msg.edit_text("⏳ AI 20 सवाल तैयार कर रहा है (Batch 2/2)...")
    
    # Batch 2: Agle 10 sawal
    batch2 = await fetch_questions_from_ai(10)

    all_questions = batch1 + batch2

    if len(all_questions) < 5: # Agar bahut kam sawal mile
        await status_msg.edit_text("❌ AI से संपर्क नहीं हो पाया। कृपया दोबारा /start करें।")
        is_bot_busy = False
        return

    await status_msg.delete()

    # 20 questions ko format karke bhejna
    full_text = f"📝 **GK QUIZ: TOTAL {len(all_questions)} QUESTIONS**\n\n"
    
    for i, q in enumerate(all_questions, 1):
        q_block = f"❓ **सवाल {i}:** {q['question']}\n"
        opts = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_block += f"   {opts[idx]}) {opt}\n"
        
        correct = opts[q['answer']]
        q_block += f"✅ **उत्तर:** {correct}\n\n"

        # Telegram length limit check
        if len(full_text) + len(q_block) > 3900:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')
            full_text = ""
        
        full_text += q_block

    if full_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🏆 **टेस्ट पूरा हुआ!** अब आप दोबारा /start कर सकते हैं।"
    )
    
    is_bot_busy = False

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
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
    except: pass
