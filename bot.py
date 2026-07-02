import os
import asyncio
import random
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, PollAnswerHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ====== राजस्थान GK - 20 सवाल ======
QUESTIONS = [
    {"question": "राजस्थान की राजधानी क्या है?", "options": ["जयपुर", "जोधपुर", "उदयपुर", "कोटा"], "correct": 0, "explanation": "जयपुर 'गुलाबी शहर' के नाम से भी प्रसिद्ध है। महाराजा सवाई जय सिंह द्वितीय ने बसाया।"},
    {"question": "राजस्थान का सबसे बड़ा जिला (क्षेत्रफल) कौन सा है?", "options": ["जोधपुर", "जैसलमेर", "बीकानेर", "बाड़मेर"], "correct": 1, "explanation": "जैसलमेर (38,401 वर्ग किमी) - थार मरुस्थल के हृदय में स्थित।"},
    {"question": "राजस्थान की सबसे लंबी नदी कौन सी है?", "options": ["चम्बल", "बनास", "लूनी", "माही"], "correct": 0, "explanation": "चम्बल नदी 966 किमी लंबी - राजस्थान, मध्य प्रदेश और उत्तर प्रदेश से बहती है।"},
    {"question": "थार मरुस्थल को और क्या कहते हैं?", "options": ["सहारा", "गोबी", "महान भारतीय मरुस्थल", "कालाहारी"], "correct": 2, "explanation": "Great Indian Desert - दुनिया का 17वां सबसे बड़ा मरुस्थल है।"},
    {"question": "राजस्थान में कुल कितने जिले हैं (2024)?", "options": ["33", "41", "50", "36"], "correct": 2, "explanation": "2023 में 17 नए जिले बनाकर कुल 50 जिले हो गए।"},
    {"question": "अरावली पर्वतमाला की सबसे ऊंची चोटी?", "options": ["सेर", "गुरु शिखर", "जरगा", "रघुनाथगढ़"], "correct": 1, "explanation": "गुरु शिखर (1722 मीटर) - माउंट आबू में स्थित।"},
    {"question": "राजस्थान की सबसे बड़ी झील कौन सी है?", "options": ["पुष्कर", "सांभर", "फतहसागर", "जयसमंद"], "correct": 1, "explanation": "सांभर झील - भारत की सबसे बड़ी खारे पानी की झील, नमक उत्पादन के लिए प्रसिद्ध।"},
    {"question": "कुम्भलगढ़ दुर्ग किसने बनवाया?", "options": ["राणा कुम्भा", "राणा सांगा", "महाराणा प्रताप", "राणा हम्मीर"], "correct": 0, "explanation": "राणा कुम्भा ने 15वीं सदी में बनवाया - दीवार इतनी लंबी कि चीन की दीवार से भी ज़्यादा मानी जाती है।"},
    {"question": "हवा महल किस शहर में है?", "options": ["जोधपुर", "उदयपुर", "जयपुर", "कोटा"], "correct": 2, "explanation": "जयपुर में - 953 छोटी खिड़कियां हैं, महाराजा सवाई प्रताप सिंह ने 1799 में बनवाया।"},
    {"question": "राजस्थान का राज्य पक्षी कौन सा है?", "options": ["मोर", "बाज", "गोडावण", "तोता"], "correct": 2, "explanation": "गोडावण (Great Indian Bustard) - विश्व में सबसे भारी उड़ने वाला पक्षी।"},
    {"question": "मेवाड़ का संस्थापक कौन था?", "options": ["बप्पा रावल", "राणा हम्मीर", "राणा कुम्भा", "राणा सांगा"], "correct": 0, "explanation": "बप्पा रावल (8वीं सदी) - कलबोज गोत्र के राजपूत।"},
    {"question": "राजस्थान दिवस कब मनाया जाता है?", "options": ["1 नवंबर", "30 मार्च", "26 जनवरी", "15 अगस्त"], "correct": 1, "explanation": "30 मार्च 1949 - जोधपुर, जयपुर, जैसलमेर और बीकानेर रियासतों का विलय हुआ।"},
    {"question": "दिलवाड़ा जैन मंदिर कहां है?", "options": ["जयपुर", "माउंट आबू", "जोधपुर", "राजसमंद"], "correct": 1, "explanation": "माउंट आबू - 11वीं-13वीं सदी के 5 भव्य जैन मंदिर।"},
    {"question": "मेहरानगढ़ दुर्ग किस शहर में है?", "options": ["जयपुर", "जोधपुर", "बीकानेर", "जैसलमेर"], "correct": 1, "explanation": "जोधपुर - राव जोधा ने 1459 में बनवाया, 125 मीटर ऊंची पहाड़ी पर।"},
    {"question": "पुष्कर मेला किस नदी के किनारे लगता है?", "options": ["बनास", "चम्बल", "पुष्कर नदी", "लूनी"], "correct": 2, "explanation": "कार्तिक पूर्णिमा पर - दुनिया का एकमात्र ब्रह्मा मंदिर यहीं है।"},
    {"question": "जवाहर सागर बांध किस नदी पर है?", "options": ["बनास", "चम्बल", "लूनी", "माही"], "correct": 1, "explanation": "कोटा में चम्बल नदी पर - राजस्थान का सबसे बड़ा बांध।"},
    {"question": "राजस्थान का राज्य खनिज कौन सा है?", "options": ["तांबा", "लोहा", "मार्बल", "सोना"], "correct": 2, "explanation": "मार्बल - मकराना का सफेद मार्बल ताजमहल में भी इस्तेमाल हुआ।"},
    {"question": "राजस्थान का सबसे गर्म जिला कौन सा है?", "options": ["जैसलमेर", "बीकानेर", "चूरू", "बाड़मेर"], "correct": 2, "explanation": "चूरू - गर्मियों में तापमान 50°C तक पहुंच जाता है।"},
    {"question": "उदयपुर को किस नाम से जानते हैं?", "options": ["गुलाबी शहर", "नीली शहर", "सफेद शहर", "सोने का शहर"], "correct": 1, "explanation": "नीली शहर - महाराणा उदय सिंह ने 1559 में बसाया, झीलों का शहर।"},
    {"question": "रणथंभोर किस जिले में है?", "options": ["अलवर", "सवाई माधोपुर", "करौली", "धौलपुर"], "correct": 1, "explanation": "सवाई माधोपुर - बाघ प्रोजेक्ट का पहला केंद्र, बाघों के लिए विश्व प्रसिद्ध।"},
]

# रंगीन मैसेज
CORRECT_MSGS = [
    "🔥 धमाकेदार! सही जवाब!",
    "💯 परफेक्ट! बिल्कुल सही!",
    "🎯 बुल्सआई! कमाल कर दिया!",
    "🧠 शानदार! गजब की याददाश्त!",
    "⚡ इलेक्ट्रिक! एकदम सही!",
    "🦁 राजस्थानी शेर! सही जवाब!",
    "👑 किंग! बिल्कुल सही!",
]

WRONG_MSGS = [
    "😅 ओह! गलत गया भाई!",
    "❌ भाई साहब, गलत जवाब!",
    "🤔 अरे! ये तो गलत है!",
    "👇 नीचे सही जवाब देखो!",
]

TIMEOUT_MSGS = [
    "⏰ बॉस समय खत्म! जल्दी करो!",
    "⌛ टाइम आउट! अगला आ रहा है!",
    "⏳ समय निकल गया! तेज़ रहो!",
]

user_data = {}

def get_menu():
    return ReplyKeyboardMarkup(
        [["📊 मेरा स्कोर", "🔄 नया शुरू"]],
        resize_keyboard=True
    )

# ====== START - ऑटो क्विज़ शुरू ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    user_data[uid] = {
        "score": 0, "total": 0, "qi": 0,
        "waiting": False, "answered": False,
        "chat_id": update.effective_chat.id,
        "msg_id": None, "next_task": None
    }

    text = f"""
╔═══════════════════════════╗
║    🏆 QUIZ CHAMPION 🏆     ║
╚═══════════════════════════╝

👤 {user.first_name} भाई!

📌 *राजस्थान GK*
📝 कुल सवाल: *{len(QUESTIONS)}*
⏱️ हर सवाल: *45 सेकंड*

✅ सही = 🟢 हरा + उछलते आइकन
❌ गलत = 🔴 लाल + वाइब्रेट
⏰ टाइम आउट = ⏰ वाइब्रेट

━━━━━━━━━━━━━━━━━━━━━
🚀 क्विज़ *अपने आप* शुरू हो रहा है...
"""
    await update.message.reply_text(text, reply_markup=get_menu(), parse_mode="Markdown")

    # 🔥 ऑटो स्टार्ट - 2 सेकंड बाद पहला सवाल
    await asyncio.sleep(2)
    await send_poll(context, uid, 0)


# ====== POLL भेजो ======
async def send_poll(context, uid, qi):
    if qi >= len(QUESTIONS):
        await show_result(context, uid)
        return

    ud = user_data[uid]

    # पुराना टाइमर कैंसल करो
    if ud.get("next_task"):
        ud["next_task"].cancel()

    q = QUESTIONS[qi]
    ud["qi"] = qi
    ud["waiting"] = True
    ud["answered"] = False
    chat_id = ud["chat_id"]
    total = len(QUESTIONS)

    # रंगीन प्रोग्रेस बार
    filled = "🟩" * (qi + 1)
    empty = "⬜" * (total - qi - 1)
    bar = f"{filled}{empty}"

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"""
📌 *राजस्थान GK* — सवाल {qi+1}/{total}

{bar}

❓ *{q['question']}*

⏱️ 45 सेकंड का समय!
👇 नीचे जवाब चुनो:
""",
        parse_mode="Markdown"
    )

    # 🎯 NATIVE QUIZ POLL - open_period=45 से 45 सेकंड बाद ऑटो बंद + वाइब्रेट
    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        explanation=q["explanation"],
        explanation_parse_mode="Markdown",
        open_period=45
    )

    ud["msg_id"] = msg.message_id

    # ⏰ 51 सेकंड बाद अगला सवाल (45 पोल + 6 पढ़ने का समय)
    ud["next_task"] = asyncio.create_task(auto_next(context, uid, qi, 51))


# ====== जवाब आया ======
async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    uid = answer.user.id

    if uid not in user_data or not user_data[uid].get("waiting"):
        return

    ud = user_data[uid]
    if ud["answered"]:
        return

    ud["answered"] = True
    ud["waiting"] = False
    qi = ud["qi"]
    q = QUESTIONS[qi]
    chat_id = ud["chat_id"]

    chosen = answer.option_ids[0]
    if chosen == q["correct"]:
        ud["score"] += 1
        msg = random.choice(CORRECT_MSGS)
    else:
        msg = random.choice(WRONG_MSGS)
    ud["total"] += 1

    # 51s वाला टाइमर कैंसल
    if ud.get("next_task"):
        ud["next_task"].cancel()

    # स्कोर भेजो
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"""
{msg}

━━━━━━━━━━━━━━━━━━━━━
📊 स्कोर: *{ud['score']}/{ud['total']}*
⏳ अगला सवाल 6 सेकंड में...
""",
        parse_mode="Markdown"
    )

    # 6 सेकंड बाद अगला सवाल
    ud["next_task"] = asyncio.create_task(auto_next(context, uid, qi, 6))


# ====== ऑटो नेक्स्ट ======
async def auto_next(context, uid, expected_qi, delay):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    ud = user_data.get(uid)
    if not ud or ud["qi"] != expected_qi:
        return

    # अगर जवाब नहीं दिया (टाइम आउट)
    if not ud["answered"] and ud["waiting"]:
        ud["waiting"] = False
        ud["total"] += 1
        await context.bot.send_message(
            chat_id=ud["chat_id"],
            text=f"""
{random.choice(TIMEOUT_MSGS)}

━━━━━━━━━━━━━━━━━━━━━
📊 स्कोर: *{ud['score']}/{ud['total']}*
⏳ अगला सवाल 4 सेकंड में...
""",
            parse_mode="Markdown"
        )
        await asyncio.sleep(4)
        await send_poll(context, uid, expected_qi + 1)
    else:
        await send_poll(context, uid, expected_qi + 1)


# ====== फाइनल रिजल्ट ======
async def show_result(context, uid):
    ud = user_data[uid]
    score = ud["score"]
    total = len(QUESTIONS)
    percent = (score / total) * 100
    chat_id = ud["chat_id"]

    if percent == 100:
        grade = "🌟 परफेक्ट स्कोर! तुम तो राजस्थान एक्सपर्ट हो!"
        stars = "⭐⭐⭐⭐⭐"
        trophy = "🥇"
    elif percent >= 80:
        grade = "🏆 शानदार! बहुत कम लोग इतने स्कोर कर पाते हैं!"
        stars = "⭐⭐⭐⭐"
        trophy = "🥈"
    elif percent >= 60:
        grade = "👍 अच्छा है! थोड़ी मेहनत और करो!"
        stars = "⭐⭐⭐"
        trophy = "🥉"
    elif percent >= 40:
        grade = "📚 ठीक है, राजस्थान की किताबें पढ़ो!"
        stars = "⭐⭐"
        trophy = "📖"
    else:
        grade = "💪 भाई राजस्थान जाओ, घूमो, देखो! फिर आओ!"
        stars = "⭐"
        trophy = "🧳"

    text = f"""
╔═══════════════════════════╗
║       🏆 रिजल्ट 🏆        ║
╚═══════════════════════════╝

{trophy}

📌 विषय: *राजस्थान GK*
📊 स्कोर: *{score}/{total}*
📈 प्रतिशत: *{percent:.0f}%*

{stars}

🏅 *{grade}*

━━━━━━━━━━━━━━━━━━━━━
🔄 दोबारा खेलने के लिए "नया शुरू" दबाओ!
"""
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_menu(), parse_mode="Markdown")


# ====== स्कोर ======
async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ud = user_data.get(uid, {"score": 0, "total": 0})
    s = ud.get("score", 0)
    t = ud.get("total", 0)
    left = len(QUESTIONS) - t

    if t == 0:
        bar = "⬜" * len(QUESTIONS)
    else:
        bar = "🟩" * s + "🟥" * (t - s) + "⬜" * left

    text = f"""
╔═══════════════════════════╗
║      📊 मेरा स्कोर       ║
╚═══════════════════════════╝

{bar}

✅ सही: *{s}*
❌ गलत: *{t - s}*
⏳ बाकी: *{left}*
📝 कुल: *{len(QUESTIONS)}*
"""
    await update.message.reply_text(text, parse_mode="Markdown")


# ====== रीसेट ======
async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # पुराना टाइमर कैंसल
    if uid in user_data and user_data[uid].get("next_task"):
        user_data[uid]["next_task"].cancel()

    user_data[uid] = {
        "score": 0, "total": 0, "qi": 0,
        "waiting": False, "answered": False,
        "chat_id": update.effective_chat.id,
        "msg_id": None, "next_task": None
    }

    await update.message.reply_text(
        "🔄 *रीसेट हो गया!*\n\n🚀 क्विज़ अपने आप शुरू हो रहा है...",
        parse_mode="Markdown"
    )

    await asyncio.sleep(2)
    await send_poll(context, uid, 0)


# ====== मेनू ======
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "📊 मेरा स्कोर":
        await show_score(update, context)
    elif t == "🔄 नया शुरू":
        await reset_cmd(update, context)


# ====== मेन ======
def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN नहीं मिला!")
        return

    print("🚀 राजस्थान GK Quiz (Auto + Vibrate) शुरू हो रहा है...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("✅ बॉट चल रहा है!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
