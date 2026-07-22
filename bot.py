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

# --- 4. असली पोल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    if index >= len(quiz_set):
        await context.bot.send_message(chat_id=chat_id, text="🏆 **रिवीजन पूरा हुआ!**\n\nनया टॉपिक शुरू करने के लिए /start दबाएँ।")
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    # भाषा रैंडमली चुनना
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    # यहाँ है असली "Telegram Native Quiz Poll"
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"({index+1}/{len(quiz_set)}) {question_text}",
        options=options,
        type=Poll.QUIZ, # यह असली क्विज़ मोड है
        correct_option_id=correct_index,
        is_anonymous=False, # ऑटो-नेक्स्ट के लिए यह ज़रूरी है
        allows_multiple_answers=False,
        explanation="सही उत्तर पर ध्यान दें! ✅", # गलत होने पर यह दिखेगा
    )
    
    user_data['current_poll_id'] = message.poll.id
    user_data['current_index'] = index + 1

# --- 5. हैंडलर्स ---

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("🔄 रिसेट सफल! अब /start दबाएँ।")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['is_busy'] = False
    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस खाली है।")
        return

    keyboard = [[InlineKeyboardButton(topic, callback_data=topic)] for topic in db.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎯 **रिवीजन शुरू करें! अपना टॉपिक चुनें:**", reply_markup=reply_markup)

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    topic_name = query.data
    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text("❌ सवाल नहीं मिले।")
        return

    # 20 सवाल रैंडम चुनना
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data['quiz_set'] = selected_qs
    context.user_data['current_index'] = 0
    context.user_data['is_busy'] = True
    context.user_data['chat_id'] = query.message.chat_id

    await query.delete_message()
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🚀 **{topic_name} क्विज़ शुरू!**")
    
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user_data = context.user_data

    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        # 1 सेकंड का गैप (पटाखे फूटने का अहसास होने दें)
        await asyncio.sleep(1)
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: pass
