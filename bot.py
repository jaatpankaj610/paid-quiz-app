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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. टोकन
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# --- 3. डेटाबेस फंक्शन ---
def load_database():
    try:
        if os.path.exists("quiz_database.json"):
            with open("quiz_database.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Database Load Error: {e}")
    return {}

# --- 4. पोल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    if index >= len(quiz_set):
        await context.bot.send_message(chat_id=chat_id, text="🏆 **रिवीजन पूरा हुआ!**\n\nअगले टॉपिक के लिए /start दबाएँ।")
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    try:
        message = await context.bot.send_poll(
            chat_id=chat_id,
            question=f"[{index+1}/{len(quiz_set)}] {question_text}",
            options=options,
            type=Poll.QUIZ,
            correct_option_id=correct_index,
            is_anonymous=False,
            explanation="सही उत्तर चुनने का प्रयास करें!"
        )
        user_data['current_poll_id'] = message.poll.id
        user_data['current_index'] = index + 1
    except Exception as e:
        logger.error(f"Poll Send Error: {e}")
        user_data['is_busy'] = False

# --- 5. रिसेट कमांड ---
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """सब कुछ क्लीन करने के लिए कमांड: /reset"""
    context.user_data.clear() # पूरा डेटा डिलीट
    context.user_data['is_busy'] = False
    await update.message.reply_text("🔄 **सब कुछ रिसेट कर दिया गया है!**\n\nअब आप नए सिरे से /start दबा सकते हैं।")

# --- 6. बाकी हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # स्टार्ट पर भी इंटरनल रिसेट
    context.user_data['is_busy'] = False
    context.user_data['current_index'] = 0
    
    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस फाइल नहीं मिली।")
        return

    keyboard = [[InlineKeyboardButton(topic, callback_data=topic)] for topic in db.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 **राम राम भाई!**\n\nटॉपिक चुनें और रिवीजन शुरू करें:",
        reply_markup=reply_markup
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    topic_name = query.data
    await query.answer()

    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text(f"❌ '{topic_name}' खाली है।")
        return

    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data['quiz_set'] = selected_qs
    context.user_data['current_index'] = 0
    context.user_data['is_busy'] = True
    context.user_data['chat_id'] = query.message.chat_id

    try: await query.delete_message()
    except: pass

    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🏁 **{topic_name}** शुरू...")
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user_data = context.user_data

    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        await asyncio.sleep(0.6)
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # कमांड्स जोड़ना
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset_command)) # रिसेट कमांड
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))

    print("✅ बोट तैयार है! रिसेट के लिए /reset कमांड का उपयोग करें।")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: pass
