import os
import json
import random
import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 2. HEALTH SERVER (Render/Koyeb के लिए) ---
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Alive!")
    def log_message(self, format, *args): return

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    httpd = HTTPServer(("0.0.0.0", port), HealthHandler)
    httpd.serve_forever()

# --- 3. DATABASE ---
def load_db():
    if os.path.exists("quiz_database.json"):
        with open("quiz_database.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

# --- 4. QUIZ LOGIC ---
async def send_q(context, chat_id):
    ud = context.user_data
    if ud.get('idx', 0) >= len(ud.get('qs', [])):
        await context.bot.send_message(chat_id, f"🏆 रिवीजन संपन्न! स्कोर: {ud.get('score', 0)}/{len(ud['qs'])}\n\nनया टॉपिक शुरू करें: /start")
        ud['busy'] = False
        return

    q = ud['qs'][ud['idx']]
    try:
        msg = await context.bot.send_poll(
            chat_id=chat_id, 
            question=f"✨ ({ud['idx']+1}/{len(ud['qs'])}) {random.choice(q['variations'])}",
            options=q['options'], 
            type=Poll.QUIZ, 
            correct_option_id=q['answer'],
            is_anonymous=False,
            explanation="पढ़ते रहें! 📚"
        )
        ud['poll_id'] = msg.poll.id
        ud['idx'] += 1
    except Exception as e:
        logger.error(f"Poll Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    db = load_db()
    if not db:
        await update.message.reply_text("❌ डेटाबेस नहीं मिला!")
        return
    
    # रंगीन बटन्स
    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥"]
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t} {random.choice(icons)}", callback_data=t)] for t in db.keys()]
    
    await update.message.reply_text("🎯 **रिवीजन मेनू**\n\nअपना टॉपिक चुनें:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = load_db()
    topic_data = db.get(query.data, [])
    if not topic_data: return
    
    qs = random.sample(topic_data, min(len(topic_data), 20))
    context.user_data.update({'qs': qs, 'idx': 0, 'score': 0, 'busy': True, 'chat_id': query.message.chat_id})
    
    await query.delete_message()
    await send_q(context, query.message.chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    ud = context.user_data
    if ud.get('busy') and ud.get('poll_id') == ans.poll_id:
        if ans.option_ids[0] == ud['qs'][ud['idx']-1]['answer']:
            ud['score'] += 1
        await asyncio.sleep(1) # एनीमेशन का समय
        await send_q(context, ud.get('chat_id'))

# --- 5. MAIN ---
async def main():
    # Health server को अलग thread में चलाना
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    
    # पुराने वेबहुक और अपडेट्स को साफ़ करना (Conflict एरर रोकने के लिए)
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic))
    app.add_handler(PollAnswerHandler(handle_ans))

    logger.info("Bot started successfully!")
    
    # Polling शुरू करना
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
