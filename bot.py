import os
import json
import random
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

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

# --- 4. बोट हैंडलर्स ---

is_bot_busy = False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    if is_bot_busy: return

    db = load_database()
    if not db:
        await update.message.reply_text("❌ 'quiz_database.json' खाली है या नहीं मिली।")
        return

    # PDF/Topic के नामों के बटन बनाना
    keyboard = []
    for topic in db.keys():
        keyboard.append([InlineKeyboardButton(topic, callback_data=topic)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📚 **अपना Topic या PDF चुनें जिसका आप टेस्ट देना चाहते हैं:**", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_topic_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_bot_busy
    query = update.callback_query
    topic_name = query.data
    await query.answer()
    
    is_bot_busy = True # लॉक चालू
    
    db = load_database()
    all_qs = db.get(topic_name, [])

    if not all_qs:
        await query.edit_message_text(f"❌ {topic_name} में कोई सवाल नहीं मिले।")
        is_bot_busy = False
        return

    await query.edit_message_text(f"🔎 **{topic_name}** से सवाल तैयार हो रहे हैं...")

    # 20 सवाल चुनना
    sample_size = min(len(all_qs), 20)
    selected_qs = random.sample(all_qs, sample_size)

    full_quiz_text = f"📝 **TEST: {topic_name}**\n━━━━━━━━━━━━━━━\n\n"
    
    for i, q in enumerate(selected_qs, 1):
        # भाषा रैंडमली बदलना
        question_text = random.choice(q['variations'])
        
        q_block = f"❓ **सवाल {i}:** {question_text}\n"
        opts_labels = ["A", "B", "C", "D"]
        for idx, opt in enumerate(q['options']):
            q_block += f"   {opts_labels[idx]}) {opt}\n"
        
        correct_ans = opts_labels[q['answer']]
        q_block += f"✅ **उत्तर:** {correct_ans}\n\n"

        if len(full_quiz_text) + len(q_block) > 3900:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=full_text, parse_mode='Markdown')
            full_quiz_text = ""
        
        full_quiz_text += q_block

    if full_quiz_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=full_quiz_text, parse_mode='Markdown')

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"🏆 **{topic_name} का टेस्ट पूरा हुआ!**\n\nनया टॉपिक चुनने के लिए /start भेजें।"
    )
    
    is_bot_busy = False # लॉक खत्म

async def ignore_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_busy: return

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_topic_selection))
    app.add_handler(MessageHandler(filters.ALL, ignore_all), group=1)

    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    try: asyncio.run(run_bot())
    except: pass
