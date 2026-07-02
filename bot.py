import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ====== क्विज़ डेटा ======
QUIZZES = {
    "🇮🇳 सामान्य ज्ञान": [
        {
            "question": "भारत की राजधानी क्या है?",
            "options": ["मुंबई", "नई दिल्ली", "कोलकाता", "चेन्नई"],
            "correct": 1,
            "explanation": "नई दिल्ली भारत की राजधानी है, जिसे 1931 में कलकत्ते से स्थानांतरित किया गया था।"
        },
        {
            "question": "भारत का राष्ट्रीय पशु कौन सा है?",
            "options": ["शेर", "हाथी", "बाघ", "मोर"],
            "correct": 2,
            "explanation": "बाघ (Royal Bengal Tiger) भारत का राष्ट्रीय पशु है।"
        },
        {
            "question": "भारत का सबसे बड़ा राज्य कौन सा है (क्षेत्रफल में)?",
            "options": ["मध्य प्रदेश", "महाराष्ट्र", "राजस्थान", "उत्तर प्रदेश"],
            "correct": 2,
            "explanation": "राजस्थान 3,42,239 वर्ग किमी क्षेत्रफल के साथ सबसे बड़ा राज्य है।"
        },
        {
            "question": "ताजमहल किसने बनवाया?",
            "options": ["अकबर", "शाहजहां", "जहांगीर", "औरंगजेब"],
            "correct": 1,
            "explanation": "शाहजहां ने अपनी बेगम मुमताज महल की याद में ताजमहल बनवाया।"
        },
        {
            "question": "भारत का संविधान कब लागू हुआ?",
            "options": ["15 अगस्त 1947", "26 जनवरी 1950", "26 नवंबर 1949", "2 अक्टूबर 1950"],
            "correct": 1,
            "explanation": "26 जनवरी 1950 को भारत का संविधान लागू हुआ, इसीलिए इस दिन को गणतंत्र दिवस मनाते हैं।"
        }
    ],
    "💻 टेक्नोलॉजी": [
        {
            "question": "Python किसने बनाया?",
            "options": ["Dennis Ritchie", "James Gosling", "Guido van Rossum", "Bjarne Stroustrup"],
            "correct": 2,
            "explanation": "Guido van Rossum ने 1991 में Python बनाया था।"
        },
        {
            "question": "HTML का फुल फॉर्म क्या है?",
            "options": ["Hyper Text Markup Language", "High Tech Modern Language", "Hyper Transfer Markup Language", "Home Tool Markup Language"],
            "correct": 0,
            "explanation": "HTML = Hyper Text Markup Language, वेब पेज बनाने की बेसिक भाषा है।"
        },
        {
            "question": "AI का फुल फॉर्म क्या है?",
            "options": ["Artificial Intelligence", "Auto Intelligence", "Advanced Information", "Applied Internet"],
            "correct": 0,
            "explanation": "AI = Artificial Intelligence, मशीनों को इंसान की तरह सोचने की तकनीक है।"
        },
        {
            "question": "दुनिया का पहला प्रोग्रामिंग भाषा कौन सी है?",
            "options": ["COBOL", "Fortran", "BASIC", "Assembly"],
            "correct": 1,
            "explanation": "Fortran (1957) को पहली हाई-लेवल प्रोग्रामिंग भाषा माना जाता है।"
        },
        {
            "question": "1 GB में कितने MB होते हैं?",
            "options": ["100 MB", "500 MB", "1024 MB", "1000 MB"],
            "correct": 2,
            "explanation": "1 GB = 1024 MB (बाइनरी सिस्टम में)"
        }
    ],
    "🎬 बॉलीवुड": [
        {
            "question": "शाहरुख खान की पहली फिल्म कौन सी है?",
            "options": ["Baazigar", "Deewana", "Darr", "Kabhi Haan Kabhi Naa"],
            "correct": 1,
            "explanation": "Deewana (1992) शाहरुख की पहली फिल्म थी।"
        },
        {
            "question": "'दंगल' फिल्म में आमिर खान किसका रोल निभाया?",
            "options": ["बॉक्सर", "पहलवान", "क्रिकेटर", "सैनिक"],
            "correct": 1,
            "explanation": "आमिर खान ने महावीर सिंह फोगाट (पहलवान) का रोल निभाया।"
        },
        {
            "question": "बॉलीवुड का 'खान' किसे कहते हैं?",
            "options": ["सलमान, शाहरुख, आमिर", "सलमान, अक्षय, रणबीर", "शाहरुख, आमिर, ऋतिक", "सलमान, शाहरुख, ऋतिक"],
            "correct": 0,
            "explanation": "सलमान खान, शाहरुख खान और आमिर खान को तीन खान कहा जाता है।"
        },
        {
            "question": "भारत की पहली टॉकी फिल्म कौन सी है?",
            "options": ["Raja Harishchandra", "Alam Ara", "Mother India", "Mughal-e-Azam"],
            "correct": 1,
            "explanation": "Alam Ara (1931) भारत की पहली बोलती फिल्म थी।"
        },
        {
            "question": "'पुष्पा' में हीरो कौन है?",
            "options": ["प्रभास", "अल्लू अर्जुन", "राम चरण", "जूनियर एनटीआर"],
            "correct": 1,
            "explanation": "अल्लू अर्जुन ने पुष्पा राज का रोल निभाया।"
        }
    ],
    "⚽ क्रिकेट": [
        {
            "question": "भारत ने पहला विश्व कप कब जीता?",
            "options": ["1983", "1987", "1992", "1996"],
            "correct": 0,
            "explanation": "1983 में कपिल देव की कप्तानी में भारत ने पहला विश्व कप जीता।"
        },
        {
            "question": "सचिन तेंदुलकर के कितने शतक हैं (ODI)?",
            "options": ["49", "51", "45", "55"],
            "correct": 0,
            "explanation": "सचिन के ODI में 49 शतक हैं, टेस्ट में 51।"
        },
        {
            "question": "IPL में सबसे ज़्यादा बार किसने जीता?",
            "options": ["CSK", "MI", "KKR", "RCB"],
            "correct": 1,
            "explanation": "मुंबई इंडियंस (MI) ने 5 बार IPL जीता है।"
        },
        {
            "question": "विराट कोहली की जन्मतिथि क्या है?",
            "options": ["5 नवंबर 1988", "5 दिसंबर 1988", "5 नवंबर 1989", "5 दिसंबर 1989"],
            "correct": 0,
            "explanation": "विराट कोहली का जन्म 5 नवंबर 1988 को दिल्ली में हुआ।"
        },
        {
            "question": "क्रिकेट में एक ओवर में कितनी गेंदें होती हैं?",
            "options": ["4", "5", "6", "8"],
            "correct": 2,
            "explanation": "एक ओवर में 6 गेंदें होती हैं (कानूनी रूप से)।"
        }
    ]
}

# यूजर डेटा
user_data = {}

# ====== मेनू बटन (नीचे हमेशा दिखेंगे) ======
def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🎮 नया क्विज़", "📊 मेरा स्कोर"],
            ["🏆 लीडरबोर्ड", "❓ हेल्प"],
            ["🔄 रीसेट"]
        ],
        resize_keyboard=True
    )

def get_back_menu():
    return ReplyKeyboardMarkup(
        [["🔙 मुख्य मेनू"]],
        resize_keyboard=True
    )


# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data[user_id] = {"score": 0, "total": 0, "category": None, "q_index": 0, "quiz_active": False}

    text = f"""
╔══════════════════════════╗
║   🏆 QUIZ CHAMPION 🏆    ║
╚══════════════════════════╝

👤 स्वागत है {user.first_name} जी!

📝 हमारे पास {len(QUIZZES)} कैटेगरी हैं
❓ हर कैटेगरी में 5 सवाल हैं
💡 हर जवाब के बाद एक्सप्लेनेशन मिलेगा
🏆 स्कोर ट्रैक होता रहेगा

━━━━━━━━━━━━━━━━━━━━
👆 नीचे बटन दबाओ!
"""
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")


# ====== कैटेगरी चुनो ======
async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"score": 0, "total": 0, "category": None, "q_index": 0, "quiz_active": False}

    text = """
📂 **कैटेगरी चुनो:**

━━━━━━━━━━━━━━━━━━━━
यहां से अपनी पसंद का विषय चुनो!
"""
    buttons = []
    for cat in QUIZZES.keys():
        buttons.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ====== सवाल भेजो ======
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, cat: str, q_index: int):
    questions = QUIZZES[cat]
    if q_index >= len(questions):
        await show_result(update, context, user_id, cat)
        return

    q = questions[q_index]
    user_data[user_id]["q_index"] = q_index
    user_data[user_id]["quiz_active"] = True

    buttons = []
    emojis = ["🅰️", "🅱️", "©️", "🅳️"]
    for i, option in enumerate(q["options"]):
        buttons.append([InlineKeyboardButton(f"{emojis[i]}  {option}", callback_data=f"ans_{i}")])

    keyboard = InlineKeyboardMarkup(buttons)

    # प्रोग्रेस बार
    total = len(questions)
    filled = "🟩" * (q_index + 1)
    empty = "⬜" * (total - q_index - 1)
    progress = f"{filled}{empty}  {q_index+1}/{total}"

    text = f"""
📌 *{cat}*

{progress}

━━━━━━━━━━━━━━━━━━━━
❓ *{q['question']}*
━━━━━━━━━━━━━━━━━━━━

⏰ सही जवाब चुनो!
"""
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ====== जवाब चेक करो ======
async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not data.startswith("ans_"):
        return

    if user_id not in user_data or not user_data[user_id].get("quiz_active"):
        await query.answer("पहले क्विज़ शुरू करो!", show_alert=True)
        return

    selected = int(data.split("_")[1])
    ud = user_data[user_id]
    cat = ud["category"]
    q_index = ud["q_index"]
    q = QUIZZES[cat][q_index]

    sahi = (selected == q["correct"])
    if sahi:
        ud["score"] += 1
    ud["total"] += 1

    if sahi:
        result = "✅ *सही जवाब!* 🎉\n🌟 +1 पॉइंट"
    else:
        result = f"❌ *गलत जवाब!*\n✅ सही जवाब: {q['options'][q['correct']]}"

    total = len(QUIZZES[cat])
    progress_filled = "🟩" * (q_index + 1)
    progress_empty = "⬜" * (total - q_index - 1)
    progress = f"{progress_filled}{progress_empty}  {q_index+1}/{total}"

    text = f"""
{result}

━━━━━━━━━━━━━━━━━━━━
💡 *एक्सप्लेनेशन:*
{q['explanation']}
━━━━━━━━━━━━━━━━━━━━

📊 स्कोर: *{ud['score']}/{ud['total']}*
{progress}
"""
    buttons = []
    if q_index + 1 < total:
        buttons.append([InlineKeyboardButton("⏭ अगला सवाल", callback_data="next_q")])
    else:
        buttons.append([InlineKeyboardButton("🏆 रिजल्ट देखो", callback_data="show_result")])

    keyboard = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


# ====== अगला सवाल ======
async def next_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ud = user_data[user_id]
    await send_question(update, context, user_id, ud["category"], ud["q_index"] + 1)


# ====== रिजल्ट ======
async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, cat: str = None):
    ud = user_data[user_id]
    if cat is None:
        cat = ud["category"]
    ud["quiz_active"] = False

    score = ud["score"]
    total = len(QUIZZES[cat])
    percent = (score / total) * 100

    if percent == 100:
        grade = "🌟 परफेक्ट स्कोर! शानदार!"
        stars = "⭐⭐⭐⭐⭐"
    elif percent >= 80:
        grade = "🏆 बहुत बढ़िया!"
        stars = "⭐⭐⭐⭐"
    elif percent >= 60:
        grade = "👍 अच्छा है!"
        stars = "⭐⭐⭐"
    elif percent >= 40:
        grade = "😐 ठीक है, और मेहनत करो"
        stars = "⭐⭐"
    else:
        grade = "💪 फिर से कोशिश करो!"
        stars = "⭐"

    text = f"""
╔══════════════════════════╗
║      🏆 रिजल्ट 🏆        ║
╚══════════════════════════╝

📌 कैटेगरी: *{cat}*

━━━━━━━━━━━━━━━━━━━━
📊 स्कोर: *{score}/{total}*
📈 प्रतिशत: *{percent:.0f}%*
━━━━━━━━━━━━━━━━━━━━

{stars}

🏅 *{grade}*

━━━━━━━━━━━━━━━━━━━━
🔄 दोबारा खेलने के लिए नीचे बटन दबाओ!
"""
    await query.message.edit_text(text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown") if update.callback_query else \
        await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")

    # रिजल्ट के बाद मेनू वापस लाओ
    if update.callback_query:
        await update.callback_query.message.reply_text("👆 नीचे से चुनो:", reply_markup=get_main_menu())


# ====== कैटेगरी हैंडलर ======
async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "show_result":
        await show_result(update, context, user_id)
        return

    if not query.data.startswith("cat_"):
        return

    cat = query.data[4:]
    user_data[user_id]["category"] = cat
    user_data[user_id]["score"] = 0
    user_data[user_id]["total"] = 0
    user_data[user_id]["q_index"] = 0

    await query.message.edit_text(f"📌 *{cat}* चुना!\n\n⏳ क्विज़ शुरू हो रहा है...", parse_mode="Markdown")
    await send_question(update, context, user_id, cat, 0)


# ====== स्कोर ======
async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ud = user_data.get(user_id, {"score": 0, "total": 0})

    total_q = sum(len(q) for q in QUIZZES.values())
    text = f"""
╔══════════════════════════╗
║     📊 मेरा स्कोर        ║
╚══════════════════════════╝

✅ सही जवाब: *{ud.get('score', 0)}*
❌ कुल प्रयास: *{ud.get('total', 0)}*

━━━━━━━━━━━━━━━━━━━━
📝 कुल सवाल उपलब्ध: *{total_q}*
📂 कैटेगरी: *{len(QUIZZES)}*
━━━━━━━━━━━━━━━━━━━━

🔄 रीसेट करने के लिए नीचे बटन दबाओ
"""
    await update.message.reply_text(text, parse_mode="Markdown")


# ====== लीडरबोर्ड ======
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
╔══════════════════════════╗
║     🏆 लीडरबोर्ड         ║
╚══════════════════════════╝

🥇 @user_one    - 45/50
🥈 @user_two    - 42/50
🥉 @user_three  - 38/50
4️⃣ @user_four   - 35/50
5️⃣ @user_five   - 30/50

━━━━━━━━━━━━━━━━━━━━
💡 ज़्यादा खेलो, लीडरबोर्ड में आओ!
"""
    await update.message.reply_text(text, parse_mode="Markdown")


# ====== हेल्प ======
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
╔══════════════════════════╗
║        ❓ हेल्प           ║
╚══════════════════════════╝

🎮 *नया क्विज़* - कैटेगरी चुनो और खेलो
📊 *मेरा स्कोर* - अपना स्कोर देखो
🏆 *लीडरबोर्ड* - टॉप खिलाड़ी देखो
🔄 *रीसेट* - स्कोर रीसेट करो

━━━━━━━━━━━━━━━━━━━━
🎯 *कैसे खेलना है:*
1️⃣ "नया क्विज़" दबाओ
2️⃣ कैटेगरी चुनो
3️⃣ 4 ऑप्शन में से सही चुनो
4️⃣ एक्सप्लेनेशन पढ़ो
5️⃣ "अगला सवाल" दबाओ
6️⃣ रिजल्ट देखो!

━━━━━━━━━━━━━━━━━━━━
📂 *कैटेगरी:*
"""
    for cat in QUIZZES.keys():
        text += f"  • {cat} ({len(QUIZZES[cat])} सवाल)\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ====== रीसेट ======
async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"score": 0, "total": 0, "category": None, "q_index": 0, "quiz_active": False}
    await update.message.reply_text("🔄 *स्कोर रीसेट हो गया!*\n\n🎮 नया क्विज़ शुरू करो!", parse_mode="Markdown")


# ====== मेनू बटन हैंडलर ======
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🎮 नया क्विज़":
        await new_quiz(update, context)
    elif text == "📊 मेरा स्कोर":
        await show_score(update, context)
    elif text == "🏆 लीडरबोर्ड":
        await leaderboard(update, context)
    elif text == "❓ हेल्प":
        await help_cmd(update, context)
    elif text == "🔄 रीसेट":
        await reset_cmd(update, context)
    elif text == "🔙 मुख्य मेनू":
        await start(update, context)


# ====== मेन ======
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN नहीं मिला!")
        return

    print("🚀 Quiz Champion Bot शुरू हो रहा है...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("✅ बॉट चल रहा है!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
