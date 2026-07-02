import os
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, PollAnswerHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ====== राजस्थान GK ======
QUESTIONS = [
    {"question": "1. राजस्थान की राजधानी क्या है?", "options": ["जयपुर", "जोधपुर", "उदयपुर", "कोटा"], "correct": 0},
    {"question": "2. राजस्थान का सबसे बड़ा जिला (क्षेत्रफल) कौन सा है?", "options": ["जोधपुर", "जैसलमेर", "बीकानेर", "बाड़मेर"], "correct": 1},
    {"question": "3. राजस्थान की सबसे लंबी नदी कौन सी है?", "options": ["चम्बल", "बनास", "लूनी", "माही"], "correct": 0},
    {"question": "4. थार मरुस्थल को और क्या कहते हैं?", "options": ["सहारा", "गोबी", "महान भारतीय मरुस्थल", "कालाहारी"], "correct": 2},
    {"question": "5. राजस्थान में कुल कितने जिले हैं (2024)?", "options": ["33", "41", "50", "36"], "correct": 2},
    {"question": "6. अरावली पर्वतमाला की सबसे ऊंची चोटी?", "options": ["सेर", "गुरु शिखर", "जरगा", "रघुनाथगढ़"], "correct": 1},
    {"question": "7. राजस्थान की सबसे बड़ी झील कौन सी है?", "options": ["पुष्कर", "सांभर", "फतहसागर", "जयसमंद"], "correct": 1},
    {"question": "8. कुम्भलगढ़ दुर्ग किसने बनवाया?", "options": ["राणा कुम्भा", "राणा सांगा", "महाराणा प्रताप", "राणा हम्मीर"], "correct": 0},
    {"question": "9. हवा महल किस शहर में है?", "options": ["जोधपुर", "उदयपुर", "जयपुर", "कोटा"], "correct": 2},
    {"question": "10. राजस्थान का राज्य पक्षी कौन सा है?", "options": ["मोर", "बाज", "गोडावण", "तोता"], "correct": 2},
    {"question": "11. मेवाड़ का संस्थापक कौन था?", "options": ["बप्पा रावल", "राणा हम्मीर", "राणा कुम्भा", "राणा सांगा"], "correct": 0},
    {"question": "12. राजस्थान दिवस कब मनाया जाता है?", "options": ["1 नवंबर", "30 मार्च", "26 जनवरी", "15 अगस्त"], "correct": 1},
    {"question": "13. दिलवाड़ा जैन मंदिर कहां है?", "options": ["जयपुर", "माउंट आबू", "जोधपुर", "राजसमंद"], "correct": 1},
    {"question": "14. मेहरानगढ़ दुर्ग किस शहर में है?", "options": ["जयपुर", "जोधपुर", "बीकानेर", "जैसलमेर"], "correct": 1},
    {"question": "15. पुष्कर मेला किस नदी के किनारे लगता है?", "options": ["बनास", "चम्बल", "पुष्कर नदी", "लूनी"], "correct": 2},
    {"question": "16. जवाहर सागर बांध किस नदी पर है?", "options": ["बनास", "चम्बल", "लूनी", "माही"], "correct": 1},
    {"question": "17. राजस्थान का राज्य खनिज कौन सा है?", "options": ["तांबा", "लोहा", "मार्बल", "सोना"], "correct": 2},
    {"question": "18. राजस्थान का सबसे गर्म जिला कौन सा है?", "options": ["जैसलमेर", "बीकानेर", "चूरू", "बाड़मेर"], "correct": 2},
    {"question": "19. उदयपुर को किस नाम से जानते हैं?", "options": ["गुलाबी शहर", "नीली शहर", "सफेद शहर", "सोने का शहर"], "correct": 1},
    {"question": "20. रणथंभोर किस जिले में है?", "options": ["अलवर", "सवाई माधोपुर", "करौली", "धौलपुर"], "correct": 1},
]

user_data = {}

def get_menu():
    return ReplyKeyboardMarkup([["📊 स्कोर", "🔄 नया शुरू"]], resize_keyboard=True)

# ====== START ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    user_data[uid] = {
        "score": 0, "total": 0, "qi": 0,
        "waiting": False, "answered": False,
        "chat_id": update.effective_chat.id,
        "next_task": None
    }

    await update.message.reply_text(
        f"🏆 *Quiz Champion*\n\n👤 {user.first_name}\n📝 राजस्थान GK ({len(QUESTIONS)} सवाल)\n⏱️ हर सवाल 45 सेकंड का\n\n🚀 शुरू हो रहा है...",
        reply_markup=get_menu(),
        parse_mode="Markdown"
    )

    await asyncio.sleep(2)
    await send_poll(context, uid, 0)

# ====== सिर्फ पोल भेजो (बिना किसी एक्स्ट्रा टेक्स्ट के) ======
async def send_poll(context, uid, qi):
    if qi >= len(QUESTIONS):
        await show_result(context, uid)
        return

    ud = user_data[uid]
    if ud.get("next_task"):
        ud["next_task"].cancel()

    q = QUESTIONS[qi]
    ud["qi"] = qi
    ud["waiting"] = True
    ud["answered"] = False

    # सिर्फ पोल भेजो - कोई हेडर नहीं, कोई फुटर नहीं
    await context.bot.send_poll(
        chat_id=ud["chat_id"],
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=45
    )

    # 51 सेकंड बाद अगला
    ud["next_task"] = asyncio.create_task(auto_next(context, uid, qi, 51))

# ====== जवाब आया - कुछ मत भेजो, बस स्कोर अपडेट करो ======
async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    uid = answer.user.id

    if uid not in user_data or not user_data[uid].get("waiting") or user_data[uid]["answered"]:
        return

    ud = user_data[uid]
    ud["answered"] = True
    ud["waiting"] = False

    if answer.option_ids[0] == QUESTIONS[ud["qi"]]["correct"]:
        ud["score"] += 1
    ud["total"] += 1

    if ud.get("next_task"):
        ud["next_task"].cancel()

    # जवाब देने के 6 सेकंड बाद अगला सवाल
    ud["next_task"] = asyncio.create_task(auto_next(context, uid, ud["qi"], 6))

# ====== ऑटो नेक्स्ट ======
async def auto_next(context, uid, expected_qi, delay):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    ud = user_data.get(uid)
    if not ud or ud["qi"] != expected_qi:
        return

    if not ud["answered"] and ud["waiting"]:
        ud["waiting"] = False
        ud["total"] += 1
        await send_poll(context, uid, expected_qi + 1)
    else:
        await send_poll(context, uid, expected_qi + 1)

# ====== स्टाइलिश रिजल्ट ======
async def show_result(context, uid):
    ud = user_data[uid]
    score = ud["score"]
    total = len(QUESTIONS)
    percent = (score / total) * 100

    if percent == 100: grade = "🏆 शानदार! परफेक्ट स्कोर!"
    elif percent >= 80: grade = "🥈 बहुत बढ़िया!"
    elif percent >= 60: grade = "🥉 अच्छा प्रयास!"
    elif percent >= 40: grade = "📚 और मेहनत करो!"
    else: grade = "🧳 राजस्थान घूमकर आओ!"

    text = f"""
┏━━━━━━━━━━━━━━━━━━━┓
┃     🏆  RESULT  🏆   ┃
┗━━━━━━━━━━━━━━━━━━━┛

📐 विषय: राजस्थान GK
📊 स्कोर: {score} / {total}
📈 प्रतिशत: {percent:.0f}%

{grade}

🔄 दोबारा खेलो → "नया शुरू"
"""
    await context.bot.send_message(
        chat_id=ud["chat_id"],
        text=text,
        reply_markup=get_menu()
    )

# ====== स्कोर ======
async def show_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ud = user_data.get(uid, {"score": 0, "total": 0})
    await update.message.reply_text(f"📊 स्कोर: {ud.get('score', 0)} / {len(QUESTIONS)}")

# ====== रीसेट ======
async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_data and user_data[uid].get("next_task"):
        user_data[uid]["next_task"].cancel()

    user_data[uid] = {
        "score": 0, "total": 0, "qi": 0,
        "waiting": False, "answered": False,
        "chat_id": update.effective_chat.id,
        "next_task": None
    }

    await update.message.reply_text("🔄 नया शुरू हो रहा है...")
    await asyncio.sleep(2)
    await send_poll(context, uid, 0)

# ====== मेनू ======
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "📊 स्कोर": await show_score(update, context)
    elif t == "🔄 नया शुरू": await reset_cmd(update, context)

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    if not TOKEN:
        print("❌ BOT_TOKEN नहीं मिला!")
        return
    print("🚀 Clean Quiz Bot शुरू...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    print("✅ बॉट चल रहा है!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
