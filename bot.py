import os
import sys
import logging
import threading
import asyncio
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 1. लॉगिंग
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = "7908449655:AAGVk4HYN98rZkJoeTtPIDHsHdmnr1hPG9w"
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# 3. Gemini Setup
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ AI Client Ready!")
except Exception as e:
    logger.error(f"❌ AI Error: {e}")

# 4. Render Health Server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive and Quiz System is running!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    httpd.serve_forever()

# --- 5. QUIZ LOGIC ---

async def generate_quiz_from_ai():
    """AI से सवाल बनवाने वाला फंक्शन"""
    prompt = """
    तुम्हें 5 बेहतरीन परीक्षा-उपयोगी (Exam-Oriented) सामान्य ज्ञान के प्रश्न (MCQs) तैयार करने हैं।
    नियम:
    1. 'ड़' की जगह हमेशा 'ड' का प्रयोग करें।
    2. आउटपुट केवल एक JSON Array होना चाहिए।
    Format: [{"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}, ...]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        # JSON साफ़ करना (कभी-कभी AI ```json ... ``` लगा देता है)
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"AI Quiz Gen Error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 राम राम भाई! आपका स्मार्ट क्विज़ बोट तैयार है।\n\n"
        "🚀 नया टेस्ट शुरू करने के लिए /test लिखें।"
    )

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("🔄 AI आपके लिए नए सवाल तैयार कर रहा है, कृपया 10-15 सेकंड रुकें...")
    
    quiz_data = await generate_quiz_from_ai()
    
    if not quiz_data:
        await msg.edit_text("❌ माफ़ी चाहता हूँ, AI से सवाल नहीं मिल पाए। कृपया दोबारा कोशिश करें।")
        return

    # डेटा स्टोर करना
    context.user_data['quiz'] = quiz_data
    context.user_data['current_q'] = 0
    context.user_data['score'] = 0

    await show_question(update, context, msg)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    q = quiz[idx]

    buttons = []
    for i, opt in enumerate(q['options']):
        buttons.append([InlineKeyboardButton(opt, callback_data=str(i))])

    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"❓ **सवाल {idx+1}/{len(quiz)}**\n\n{q['question']}"

    if message_obj:
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_ans = int(query.data)
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    correct_ans = quiz[idx]['answer']

    if user_ans == correct_ans:
        context.user_data['score'] += 1
        result_text = "✅ सही जवाब!"
    else:
        result_text = f"❌ गलत! सही जवाब था: {quiz[idx]['options'][correct_ans]}"

    # अगले सवाल पर बढ़ें या खत्म करें
    context.user_data['current_q'] += 1
    
    if context.user_data['current_q'] < len(quiz):
        # छोटा सा डिले ताकि यूजर अपना रिजल्ट देख सके
        await query.message.edit_text(f"{result_text}\n\nअगला सवाल आ रहा है...")
        await asyncio.sleep(1.5)
        await show_question(update, context)
    else:
        score = context.user_data['score']
        total = len(quiz)
        await query.message.edit_text(
            f"{result_text}\n\n🏆 **क्विज़ खत्म!**\nआपका स्कोर: {score}/{total}\n\nनया टेस्ट: /test"
        )

# 6. Main Runner
async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", start_test))
    app.add_handler(CallbackQueryHandler(handle_answer))
    
    async with app:
        await app.initialize()
        await app.start()
        logger.info("🤖 AI Quiz Bot is Live!")
        await app.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.critical(f"Crash: {e}")
        sys.exit(1)
