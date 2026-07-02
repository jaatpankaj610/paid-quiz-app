import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, PollAnswerHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ====== क्विज़ डेटा ======
QUIZZES = {
    "🇮🇳 सामान्य ज्ञान": [
        {"question": "भारत की राजधानी क्या है?", "options": ["मुंबई", "नई दिल्ली", "कोलकाता", "चेन्नई"], "correct": 1, "explanation": "नई दिल्ली भारत की राजधानी है, 1931 में कलकत्ते से स्थानांतरित किया गया।"},
        {"question": "भारत का राष्ट्रीय पशु कौन सा है?", "options": ["शेर", "हाथी", "बाघ", "मोर"], "correct": 2, "explanation": "बाघ (Royal Bengal Tiger) भारत का राष्ट्रीय पशु है।"},
        {"question": "भारत का सबसे बड़ा राज्य (क्षेत्रफल)?", "options": ["मध्य प्रदेश", "महाराष्ट्र", "राजस्थान", "उत्तर प्रदेश"], "correct": 2, "explanation": "राजस्थान 3,42,239 वर्ग किमी के साथ सबसे बड़ा राज्य है।"},
        {"question": "ताजमहल किसने बनवाया?", "options": ["अकबर", "शाहजहां", "जहांगीर", "औरंगजेब"], "correct": 1, "explanation": "शाहजहां ने मुमताज महल की याद में ताजमहल बनवाया।"},
        {"question": "भारत का संविधान कब लागू हुआ?", "options": ["15 अगस्त 1947", "26 जनवरी 1950", "26 नवंबर 1949", "2 अक्टूबर 1950"], "correct": 1, "explanation": "26 जनवरी 1950 को संविधान लागू हुआ - गणतंत्र दिवस!"},
    ],
    "💻 टेक्नोलॉजी": [
        {"question": "Python किसने बनाया?", "options": ["Dennis Ritchie", "James Gosling", "Guido van Rossum", "Bjarne Stroustrup"], "correct": 2, "explanation": "Guido van Rossum ने 1991 में Python बनाया।"},
        {"question": "HTML का फुल फॉर्म?", "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Hyper Transfer Markup Language", "Home Tool Markup Language"], "correct": 0, "explanation": "HTML = Hyper Text Markup Language, वेब पेज बनाने की भाषा।"},
        {"question": "AI का फुल फॉर्म?", "options": ["Artificial Intelligence", "Auto Intelligence", "Advanced Information", "Applied Internet"], "correct": 0, "explanation": "AI = Artificial Intelligence, मशीनों को सोचने की तकनीक।"},
        {"question": "दुनिया की पहली प्रोग्रामिंग भाषा?", "options": ["COBOL", "Fortran", "BASIC", "Assembly"], "correct": 1, "explanation": "Fortran (1957) पहली हाई-लेवल प्रोग्रामिंग भाषा।"},
        {"question": "1 GB में कितने MB?", "options": ["100 MB", "500 MB", "1024 MB", "1000 MB"], "correct": 2, "explanation": "1 GB = 1024 MB (बाइनरी सिस्टम)।"},
    ],
    "🎬 बॉलीवुड": [
        {"question": "शाहरुख खान की पहली फिल्म?", "options": ["Baazigar", "Deewana", "Darr", "Kabhi Haan Kabhi Naa"], "correct": 1, "explanation": "Deewana (1992) शाहरुख की पहली फिल्म।"},
        {"question": "दंगल में आमिर खान किसका रोल?", "options": ["बॉक्सर", "पहलवान", "क्रिकेटर", "सैनिक"], "correct": 1, "explanation": "महावीर सिंह फोगाट (पहलवान) का रोल।"},
        {"question": "तीन खान कौन हैं?", "options": ["सलमान, शाहरुख, आमिर", "सलमान, अक्षय, रणबीर", "शाहरुख, आमिर, ऋतिक", "सलमान, शाहरुख, ऋतिक"], "correct": 0, "explanation": "सलमान, शाहरुख, आमिर - तीन खान!"},
        {"question": "भारत की पहली टॉकी फिल्म?", "options": ["Raja Harishchandra", "Alam Ara", "Mother India", "Mughal-e-Azam"], "correct": 1, "explanation": "Alam Ara (1931) भारत की पहली बोलती फिल्म।"},
        {"question": "पुष्पा में हीरो कौन है?", "options": ["प्रभास", "अल्लू अर्जुन", "राम चरण", "जूनियर एनटीआर"], "correct": 1, "explanation": "अल्लू अर्जुन ने पुष्पा राज का रोल निभाया।"},
    ],
    "⚽ क्रिकेट": [
        {"question": "भारत ने पहला विश्व कप कब जीता?", "options": ["1983", "1987", "1992", "1996"], "correct": 0, "explanation": "1983 में कपिल देव की कप्तानी में!"},
        {"question": "सचिन के कितने ODI शतक?", "options": ["49", "51", "45", "55"], "correct": 0, "explanation": "सचिन के ODI में 49, टेस्ट में 51 शतक।"},
        {"question": "IPL में सबसे ज़्यादा बार जीतने वाली टीम?", "options": ["CSK", "MI", "KKR", "RCB"], "correct": 1, "explanation": "मुंबई इंडियंस ने 5 बार जीता!"},
        {"question": "विराट कोहली की जन्मतिथि?", "options": ["5 नवंबर 1988", "5 दिसंबर 1988", "5 नवंबर 1989", "5 दिसंबर 1989"], "correct": 0, "explanation": "5 नवंबर 1988, दिल्ली में जन्म।"},
        {"question": "एक ओवर में कितनी गेंदें?", "options": ["4", "5", "6", "8"], "correct": 2, "explanation": "एक ओवर = 6 गेंदें।"},
    ],
}

user_data = {}

def get_main_menu():
    return ReplyKeyboardMarkup(
        [["🎮 नया क्विज़", "📊 मेरा स्कोर"], ["🔄 रीसेट"]],
        resize_keyboard=True
    )

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    user_data[uid] = {"score": 0, "total": 0, "cat": None, "qi": 0, "waiting": False, "chat_id": update.effective_chat.id}
    total_q = sum(len(q) for q in QUIZZES.values())
    text = f"""
╔══════════════════════════╗
║   🏆 QUIZ CHAMPION 🏆    ║
╚══════════════════════════╝

👤 स्वागत है {user.first_name} जी!

📂 {len(QUIZZES)} कैटेगरी | 📝 {total_q} सवाल
✅ सही = हरा रंग + उछलते आइकन
❌ गलत = लाल रंग
💡 हर जवाब के बाद एक्सप्लेनेशन

━━━━━━━━━━━━━━━━━━━━
👆 नीचे "नया क्विज़" दबाओ!
"""
    await update.message.reply_text(text, reply_markup=get_main_menu())

# ====== कैटेगरी दिखाओ ======
async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📂 *कैटेगरी चुनो:*\n\n"
    for cat, qs in QUIZZES.items():
        text += f"  {cat} — {len(qs)} सवाल\n"
    text += "\n👇 नीचे से चुनो:"
    buttons = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in QUIZZES]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

# ====== कैटेगरी चुना ======
async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    if not query.data.startswith("cat_"):
        return
    cat = query.data[4:]
    ud = user_data[uid]
    ud["cat"] = cat
    ud["score"] = 0
    ud["total"] = 0
    ud["qi"] = 0
    ud["chat_id"] = query.message.chat_id

    await query.message.edit_text(f"📌 *{cat}* चुना!\n\n⏳ क्विज़ शुरू हो रहा है...", parse_mode="Markdown")
    await asyncio.sleep(1)
    await send_poll_question(context, uid, cat, 0)

# ====== POLL भेजो (यही मेन है!) ======
async def send_poll_question(context, uid, cat, qi):
    q = QUIZZES[cat][qi]
    ud = user_data[uid]
    ud["qi"] = qi
    ud["waiting"] = True
    chat_id = ud["chat_id"]
    total = len(QUIZZES[cat])
    bar = "🟩" * (qi + 1) + "⬜" * (total - qi - 1)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📌 *{cat}*\n{bar}  सवाल {qi+1}/{total}",
        parse_mode="Markdown"
    )
    await context.bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        explanation=q["explanation"],
        explanation_parse_mode="Markdown"
    )

# ====== जवाब आया (पोल एंसर) ======
async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    uid = answer.user.id
    if uid not in user_data or not user_data[uid].get("waiting"):
        return

    ud = user_data[uid]
    ud["waiting"] = False
    cat = ud["cat"]
    qi = ud["qi"]
    q = QUIZZES[cat][qi]
    chat_id = ud["chat_id"]

    chosen = answer.option_ids[0]
    if chosen == q["correct"]:
        ud["score"] += 1
        emoji = "✅"
    else:
        emoji = "❌"
    ud["total"] += 1

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"{emoji} स्कोर: *{ud['score']}/{ud['total']}*",
        parse_mode="Markdown"
    )

    # अगला सवाल या रिजल्ट
    if qi + 1 < len(QUIZZES[cat]):
        await asyncio.sleep(2)
        await send_poll_question(context, uid, cat, qi + 1)
    else:
        await asyncio.sleep(1)
        await show_final_result(context, uid, cat)

# ====== फाइनल रिजल्ट ======
async def show_final_result(context, uid, cat):
    ud = user_data[uid]
    score = ud["score"]
    total = len(QUIZZES[cat])
    percent = (score / total) * 100
    chat_id = ud["chat_id"]

    if percent == 100:
        grade = "🌟 परफेक्ट! शानदार!"
        stars = "⭐⭐⭐⭐⭐"
    elif percent >= 80:
        grade = "🏆 बहुत बढ़िया!"
        stars = "⭐⭐⭐⭐"
    elif percent >= 60:
        grade = "👍 अच्छा है!"
        stars = "⭐⭐⭐"
    elif percent >= 40:
        grade = "😐 ठीक है"
        stars = "⭐⭐"
    else:
        grade = "💪 फिर कोशिश करो!"
        stars = "⭐"

    text = f"""
╔══════════════════════════╗
║      🏆 रिजल्ट 🏆        ║
╚══════════════════════════╝

📌 कैटेगरी: *{cat}*
📊 स्कोर: *{score}/{total}*
📈 प्रतिशत: *{percent:.0f}%*
{stars}
🏅 *{grade}*

━━━━━━━━━━━━━━━━━━━━
🔄 दोबारा खेलो → "नया क्विज़" दबाओ
"""
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_main_menu(), parse_mode="Markdown")

# ====== स्कोर ======
async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ud = user_data.get(uid, {"score": 0, "total": 0})
    text = f"""
╔══════════════════════════╗
║     📊 मेरा स्कोर        ║
╚══════════════════════════╝

✅ सही जवाब: *{ud.get('score', 0)}*
📝 कुल प्रयास: *{ud.get('total', 0)}*
"""
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

# ====== रीसेट ======
async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data[uid] = {"score": 0, "total": 0, "cat": None, "qi": 0, "waiting": False, "chat_id": update.effective_chat.id}
    await update.message.reply_text("🔄 *स्कोर रीसेट हो गया!*\n\n🎮 नया क्विज़ शुरू करो!", reply_markup=get_main_menu(), parse_mode="Markdown")

# ====== मेनू बटन ======
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🎮 नया क्विज़":
        await new_quiz(update, context)
    elif text == "📊 मेरा स्कोर":
        await show_score(update, context)
    elif text == "🔄 रीसेट":
        await reset_cmd(update, context)

# ====== मेन ======
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN नहीं मिला!")
        return
    print("🚀 Quiz Champion शुरू हो रहा है...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_handler))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    print("✅ बॉट चल रहा है!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
