import os
import json
import random
import logging
import asyncio
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

# --- 3. डेटाबेस लोड करना ---
def load_database():
    if os.path.exists("quiz_database.json"):
        with open("quiz_database.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

# --- 4. पोल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id, user_id):
    data = context.user_data.get('quiz_set')
    index = context.user_data.get('current_index', 0)

    if index >= len(data):
        await context.bot.send_message(chat_id=chat_id, text="🏆 **क्विज़ पूरा हुआ!**\n\nशानदार प्रदर्शन! नया टॉपिक शुरू करने के लिए /start दबाएँ।")
        context.user_data['is_busy'] = False
        return

    q = data[index]
    # रैंडम भाषा (Variation) चुनना
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    # टेलीग्राम क्विज़ पोल भेजना
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"[{index+1}/{len(data)}] {question_text}",
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_index,
        is_anonymous=False, # ताकि बॉट को पता चले आपने जवाब दे दिया
        explanation="सही उत्तर चुनने का प्रयास करें!"
    )
    
    # ट्रैक करने के लिए स्टोर करना
    context.user_data['current_poll_id'] = message.poll.id
    context.user_data['current_index'] = index + 1

# --- 5. बॉट हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('is_busy'): return

    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस फाइल नहीं मिली।")
        return

    keyboard = [[InlineKeyboardButton(topic, callback_data=topic)] for topic in db.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("📚 **किस टॉपिक का टेस्ट देना चाहते हैं?**", reply_markup=reply_markup)

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    topic_name = query.data
    await query.answer()

    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text("❌ कोई सवाल नहीं मिले।")
        return

    # 20 रैंडम सवाल सेट करना
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data['quiz_set'] = selected_qs
    context.user_data['current_index'] = 0
    context.user_data['is_busy'] = True
    context.user_data['chat_id'] = query.message.chat_id

    await query.delete_message()
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🏁 **{topic_name} क्विज़ शुरू हो रहा है...**")
    
    # पहला सवाल भेजें
    await send_next_question(context, query.message.chat_id, update.effective_user.id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जैसे ही यूजर पोल पर क्लिक करेगा, यह फंक्शन चलेगा"""
    poll_answer = update.poll_answer
    user_data = context.user_data

    # चेक करें कि क्या यह उसी पोल का जवाब है जो अभी चल रहा है
    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        # थोड़ा सा इंतज़ार (0.5 सेकंड) ताकि यूजर को पटाखे फूटते हुए दिखें
        await asyncio.sleep(0.5)
        # अगला सवाल भेजें
        await send_next_question(context, user_data.get('chat_id'), poll_answer.user.id)

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('is_busy'): return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer)) # जवाब ट्रैक करने के लिए
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: pass
