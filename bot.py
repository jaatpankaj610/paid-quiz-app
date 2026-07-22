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

# 3. हेल्थ सर्वर
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
    return "भारत का इतिहास, भूगोल और सामान्य ज्ञान।"

async def generate_20_questions():
    user_facts = load_user_facts()
    
    # Updated Prompt for better JSON reliability
    prompt = f"""
    Generate 20 GK MCQs in Hindi based on these facts: {user_facts}.
    Return ONLY a JSON array. No conversational text.
    Use 'ड' instead of 'ड़'.
    Format: [{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}]
    """
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=prompt
        )
        
        raw_text = response.text.strip()
        # Clean the response to find the JSON array
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            json_str = match.group()
            return json.loads(json_str)
        else:
            logger.error(f"No JSON found in response: {raw_text}")
            return None
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return None

# --- 5. BOT HANDLERS ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    
    if is_bot_busy:
        return # Ignore any commands while busy

    is_bot_busy = True
    user_id = update.effective_user.id
    
    status_msg = await update.message.reply_text("⏳ AI 20 सवाल तैयार कर रहा है... इसमें 30 सेकंड लग सकते हैं।\n\nकृपया इंतज़ार करें, बाकी कमांड्स अभी बंद हैं।")

    quiz_data = await generate_20_questions()

    if not quiz_data:
        await status_msg.edit_text("❌ AI से संपर्क नहीं हो पाया या डाटा गलत मिला। कृपया एक बार फिर /start टाइप करें।")
        is_bot_busy = False
        return

    # Process and Send Questions
    await status_msg.delete() # Delete the "Processing" message
    
    full_quiz_text = "📝 **GK QUIZ - 20 QUESTIONS** 📝\n\n"
    
    for i, q in enumerate(quiz_data, 1):
        try:
            q_text = f"❓ **सवाल {i}:** {q['question']}\n"
            opts = ["A", "B", "C", "D"]
            for idx, opt in enumerate(q['options']):
                q_text += f"   {opts[idx]}) {opt}\n"
            
            correct_ans = opts[q['answer']]
            q_text += f"✅ **सही उत्तर:** {correct_ans}\n\n"
            
            # Agar message bada ho jaye to bhej do aur naya start karo
            if len(full_quiz_text) + len(q_text) > 3800:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=full_quiz_text, parse_mode='Markdown')
                full_quiz_text = ""
            
            full_quiz_text += q_text
        except Exception as e:
            logger.error(f"Error formatting question {i}: {e}")

    if full_quiz_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_quiz_text, parse_mode='Markdown')

    # Final Screen
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🏆 **सभी 20 सवाल ऊपर दे दिए गए हैं!**\n\nअब आप दोबारा /start कर सकते हैं।"
    )
    
    is_bot_busy = False # Unlock the bot

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy:
        return # Do nothing

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # First priority: start command
    app.add_handler(CommandHandler("start", start))
    
    # Second priority: ignore everything else when busy
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
    except (KeyboardInterrupt, SystemExit):
        pass
