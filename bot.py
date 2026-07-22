import os
import json
import random
import logging
import asyncio
import requests
from flask import Flask, request
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PollAnswerHandler, ContextTypes

# 1. लॉगिंग सेटअप
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. कॉन्फ़िगरेशन (RENDER की सेटिंग्स)
TOKEN = "7908449655:AAGVk4HYN98rZkJoeTtPIdHsHdmnrlhPG9w"
GITHUB_URL = "https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/main/quiz_database.json"
# यहाँ अपने Render ऐप का नाम बदलें (उदा: 'your-app-name.onrender.com')
RENDER_APP_NAME = "paid-quiz-app-p7y9" 
WEBHOOK_URL = f"https://{RENDER_APP_NAME}.onrender.com/{TOKEN}"

# Flask App (Health Check और Webhook रिसीवर के लिए)
app = Flask(__name__)

# 3. डाटाबेस लोडर
def load_db():
    try:
        r = requests.get(GITHUB_URL)
        return r.json()
    except Exception as e:
        logger.error(f"DB Load Error: {e}")
        return {}

# 4. क्विज़ लॉजिक (वही रहेगा जो आपने बनाया है)
async def send_q(context, chat_id):
    ud = context.application.user_data.get(chat_id)
    if not ud: return
    
    qs = ud.get('qs', [])
    idx = ud.get('idx', 0)

    if idx >= len(qs):
        score = ud.get('score', 0)
        await context.bot.send_message(chat_id, f"🎊 **रिवीजन संपन्न!**\n\n📊 स्कोर: `{score}/{len(qs)}` सही\n\nनया टॉपिक चुनने के लिए /start दबाएँ।")
        ud['busy'] = False
        return

    q = qs[idx]
    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"✨ ({idx+1}/{len(qs)}) {random.choice(q['variations'])}",
        options=q['options'],
        type=Poll.QUIZ,
        correct_option_id=q['answer'],
        is_anonymous=False,
        explanation="मेहनत का फल मीठा होता है! 📚"
    )
    ud['poll_id'] = msg.poll.id
    ud['idx'] = idx + 1

# 5. हैंडलर्स
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.application.user_data[chat_id] = {'busy': False}
    
    db = load_db()
    if not db:
        await update.message.reply_text("❌ डेटाबेस फाइल नहीं मिली!")
        return

    icons = ["🔴", "🔵", "🟢", "🟡", "🟣", "💎", "🔥", "🌈"]
    keyboard = [[InlineKeyboardButton(f"{random.choice(icons)} {t}", callback_data=t)] for t in db.keys()]
    
    await update.message.reply_text("🎯 **रिवीजन शुरू करें! अपना टॉपिक चुनें:**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    db = load_db()
    topic_data = db.get(query.data, [])
    
    qs = random.sample(topic_data, min(len(topic_data), 20))
    context.application.user_data[chat_id].update({'qs': qs, 'idx': 0, 'score': 0, 'busy': True, 'chat_id': chat_id})
    
    await query.delete_message()
    await send_q(context, chat_id)

async def handle_ans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    # सभी यूज़र्स के डेटा में से सही यूज़र ढूंढना
    for chat_id, ud in context.application.user_data.items():
        if ud.get('busy') and ud.get('poll_id') == ans.poll_id:
            idx = ud['idx'] - 1
            if ans.option_ids[0] == ud['qs'][idx]['answer']:
                ud['score'] += 1
            await asyncio.sleep(1.2)
            await send_q(context, chat_id)
            break

# 6. MAIN (WEBHOOK के साथ)
async def main():
    # Application बनाना
    application = Application.builder().token(TOKEN).build()
    
    # हैंडलर्स जोड़ना
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_topic))
    application.add_handler(PollAnswerHandler(handle_ans))

    # पुराने सारे अपडेट्स डिलीट करना ताकि पिछला कोई मैसेज पेंडिंग न रहे
    await application.bot.delete_webhook(drop_pending_updates=True)
    
    # Webhook सेटअप करना
    # यह कमांड टेलीग्राम को बोलेगा कि सिर्फ इसी URL पर मैसेज भेजो
    await application.bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)

    # Render पर पोर्ट 10000 का इस्तेमाल
    port = int(os.environ.get("PORT", 10000))
    
    # Webhook चलाना (यह 'Conflict' को हमेशा के लिए खत्म कर देगा)
    await application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
