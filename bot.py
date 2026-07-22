import os
import json
import random
import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    PollAnswerHandler, 
    ContextTypes, 
    MessageHandler, 
    filters
)

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. टोकन
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 3. HEALTH CHECK SERVER (Render को Live रखने के लिए और Conflict रोकने के लिए) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Alive!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    httpd = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    httpd.serve_forever()

# --- 4. डेटाबेस लोड करना ---
def load_database():
    if os.path.exists("quiz_database.json"):
        with open("quiz_database.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

# --- 5. अगला सवाल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    if index >= len(quiz_set):
        score = user_data.get('score', 0)
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"🎊 **क्विज़ संपन्न!** 🎊\n\n📊 स्कोर: `{score}/{len(quiz_set)}`\n\nनया टॉपिक: /start",
            parse_mode='Markdown'
        )
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    question_text = random.choice(q['variations'])
    
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"✨ ({index+1}/{len(quiz_set)}) {question_text}",
        options=q['options'],
        type=Poll.QUIZ,
        correct_option_id=q['answer'],
        is_anonymous=False,
        explanation="मेहनत जारी रखें! 📚"
    )
    user_data['current_poll_id'] = message.poll.id
    user_data['current_index'] = index + 1

# --- 6. हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['is_busy'] = False
    context.user_data['score'] = 0
    
    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस नहीं मिला।")
        return

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = []
    for topic in db.keys():
        icon = random.choice(icons)
        keyboard.append([InlineKeyboardButton(f"{icon} {topic} {icon}", callback_data=topic)])
    
    await update.message.reply_text(
        "🎯 **रिवीजन मेनू**\nअपना टॉपिक चुनें और शुरू करें:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(text="🚀 शुरू हो रहा है...")
    
    topic_name = query.data
    db = load_database()
    all_qs = db.get(topic_name, [])
    if not all_qs: return

    selected_qs = random.sample(all_qs, min(len(all_qs), 20))
    context.user_data.update({
        'quiz_set': selected_qs, 'current_index': 0, 'is_busy': True, 
        'chat_id': query.message.chat_id, 'score': 0
    })

    await query.delete_message()
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user_data = context.user_data
    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        idx = user_data['current_index'] - 1
        if poll_answer.option_ids[0] == user_data['quiz_set'][idx]['answer']:
            user_data['score'] += 1
        await asyncio.sleep(1.2)
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Token Not Found!")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))
    
    await app.initialize()
    await app.start()
    # drop_pending_updates=True पुराने अटके मैसेज हटा देगा
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    # Health Server चालू करना ताकि Render को पोर्ट मिले
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(run_bot())
    except:
        pass
