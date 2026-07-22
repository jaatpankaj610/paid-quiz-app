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

# --- 4. अगला सवाल भेजने का फंक्शन ---
async def send_next_question(context: ContextTypes.DEFAULT_TYPE, chat_id):
    user_data = context.user_data
    quiz_set = user_data.get('quiz_set', [])
    index = user_data.get('current_index', 0)

    # अगर क्विज़ खत्म हो गया तो स्कोर दिखाओ
    if index >= len(quiz_set):
        score = user_data.get('score', 0)
        total = len(quiz_set)
        percentage = (score / total) * 100
        
        result_text = (
            f"🎊 **क्विज़ संपन्न!** 🎊\n\n"
            f"📊 **आपका स्कोर कार्ड:**\n"
            f"━━━━━━━━━━━━━━\n"
            f"✅ सही उत्तर: `{score}`\n"
            f"❌ कुल सवाल: `{total}`\n"
            f"📈 प्रतिशत: `{percentage:.1f}%`\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"बधाई हो! नया टॉपिक शुरू करने के लिए /start दबाएँ।"
        )
        await context.bot.send_message(chat_id=chat_id, text=result_text, parse_mode='Markdown')
        user_data['is_busy'] = False
        return

    q = quiz_set[index]
    question_text = random.choice(q['variations'])
    options = q['options']
    correct_index = q['answer']

    # असली क्विज़ पोल
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"✨ ({index+1}/{len(quiz_set)}) {question_text}",
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_index,
        is_anonymous=False,
        explanation="मेहनत जारी रखें! 📚✨"
    )
    
    user_data['current_poll_id'] = message.poll.id
    user_data['current_index'] = index + 1

# --- 5. हैंडलर्स ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['is_busy'] = False
    context.user_data['score'] = 0 # स्कोर रिसेट
    
    db = load_database()
    if not db:
        await update.message.reply_text("❌ डेटाबेस खाली है।")
        return

    # रंगीन बटन डिज़ाइन (Emoji based)
    colors = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "💎", "🔥", "🌈"]
    keyboard = []
    for topic in db.keys():
        icon = random.choice(colors)
        keyboard.append([InlineKeyboardButton(f"{icon} {topic} {icon}", callback_data=topic)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚡️ **SWAG REVISION BOT** ⚡️\n\n"
        "नीचे दिए गए रंगीन टॉपिक्स में से अपना पसंदीदा चुनें और वाइब्रेंट रिवीजन शुरू करें! 👇",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # क्लिक पर फीडबैक (वाइब्रेशन जैसा फील देगा)
    await query.answer(text="🚀 रिवीजन शुरू हो रहा है! तैयार हो जाइए...", show_alert=False)
    
    topic_name = query.data
    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text("❌ सवाल नहीं मिले।")
        return

    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    context.user_data.update({
        'quiz_set': selected_qs,
        'current_index': 0,
        'is_busy': True,
        'chat_id': query.message.chat_id,
        'score': 0
    })

    await query.delete_message()
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"🔥 **Topic: {topic_name}** 🔥\n3... 2... 1... GO!")
    
    await send_next_question(context, query.message.chat_id)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll_answer = update.poll_answer
    user_data = context.user_data

    if user_data.get('is_busy') and user_data.get('current_poll_id') == poll_answer.poll_id:
        # स्कोर चेक करना (सिर्फ सही उत्तर पर बढ़ेगा)
        quiz_set = user_data.get('quiz_set')
        current_idx = user_data.get('current_index') - 1
        correct_idx = quiz_set[current_idx]['answer']
        
        if poll_answer.option_ids[0] == correct_idx:
            user_data['score'] = user_data.get('score', 0) + 1
            
        # 1.2 सेकंड का इंतज़ार (ताकि एनीमेशन दिखे)
        await asyncio.sleep(1.2)
        await send_next_question(context, user_data.get('chat_id'))

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(PollAnswerHandler(handle_answer))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: pass
