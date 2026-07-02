import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== यहाँ अपने Questions डालो ======
QUIZZES = [
    {
        "question": "🇮🇳 भारत की राजधानी क्या है?",
        "options": ["मुंबई", "नई दिल्ली", "कोलकाता", "चेन्नई"],
        "correct": 1,
        "explanation": "नई दिल्ली भारत की राजधानी है।"
    },
    {
        "question": "💻 Python किसने बनाया?",
        "options": ["Dennis Ritchie", "James Gosling", "Guido van Rossum", "Bjarne Stroustrup"],
        "correct": 2,
        "explanation": "Guido van Rossum ने 1991 में Python बनाया था।"
    },
    {
        "question": "🌍 दुनिया का सबसे बड़ा महासागर कौन सा है?",
        "options": ["अटलांटिक", "हिंद महासागर", "आर्कटिक", "प्रशांत महासागर"],
        "correct": 3,
        "explanation": "प्रशांत महासागर (Pacific Ocean) सबसे बड़ा है।"
    },
    {
        "question": "🚀 ISRO का फुल फॉर्म क्या है?",
        "options": [
            "Indian Space Research Organisation",
            "International Space Research Organisation",
            "Indian Scientific Research Organisation",
            "Indian Space Rocket Organisation"
        ],
        "correct": 0,
        "explanation": "ISRO = Indian Space Research Organisation"
    },
    {
        "question": "⚡ HTML का फुल फॉर्म क्या है?",
        "options": [
            "Hyper Text Markup Language",
            "High Tech Modern Language",
            "Hyper Transfer Markup Language",
            "Home Tool Markup Language"
        ],
        "correct": 0,
        "explanation": "HTML = Hyper Text Markup Language"
    }
]

# यूजर का स्कोर और कौन सा सवाल है ये याद रखेंगे
user_scores = {}
user_current_q = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जब कोई /start भेजे"""
    user = update.effective_user
    text = f"""
🎮 **Quiz Bot में आपका स्वागत है!**

👤 {user.first_name} जी,

📝 कुल सवाल: {len(QUIZZES)}
💡 हर सवाल के बाद जवाब की वजह बताएंगे

👉 **/quiz** - क्विज़ शुरू करो
📊 **/score** - अपना स्कोर देखो
🔄 **/reset** - स्कोर रीसेट करो
❓ **/help** - हेल्प देखो
"""
    await update.message.reply_text(text, parse_mode="Markdown")


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """क्विज़ शुरू करो"""
    user_id = update.effective_user.id
    user_current_q[user_id] = 0
    user_scores[user_id] = 0
    await send_question(update, context, user_id, 0)


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, q_index: int):
    """सवाल भेजो बटन के साथ"""
    if q_index >= len(QUIZZES):
        await show_result(update, context, user_id)
        return

    q = QUIZZES[q_index]
    user_current_q[user_id] = q_index

    # 4 बटन बनाओ
    buttons = []
    for i, option in enumerate(q["options"]):
        buttons.append([InlineKeyboardButton(
            f"{['🅰️', '🅱️', '©️', '🅳️'][i]} {option}",
            callback_data=f"ans_{q_index}_{i}"
        )])

    keyboard = InlineKeyboardMarkup(buttons)
    text = f"❓ **सवाल {q_index + 1}/{len(QUIZZES)}**\n\n{q['question']}\n\n⏰ सही जवाब चुनो!"

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """जब यूजर कोई बटन दबाए"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data.split("_")

    if data[0] != "ans":
        return

    q_index = int(data[1])
    selected = int(data[2])

    if user_current_q.get(user_id) != q_index:
        await query.answer("पहले पुराने सवाल का जवाब दो!", show_alert=True)
        return

    q = QUIZZES[q_index]
    sahi = (selected == q["correct"])

    if sahi:
        user_scores[user_id] = user_scores.get(user_id, 0) + 1
        result = "✅ **सही जवाब!** 🎉"
    else:
        result = f"❌ **गलत जवाब!**\n✅ सही जवाब: {q['options'][q['correct']]}"

    text = f"""
{result}

💡 **वजह:**
{q['explanation']}

━━━━━━━━━━━━━━━
📊 स्कोर: {user_scores.get(user_id, 0)}/{q_index + 1}

⏭ अगले सवाल के लिए बटन दबाओ:
"""
    buttons = [[InlineKeyboardButton("⏭ अगला सवाल", callback_data=f"next_{q_index + 1}")]]
    keyboard = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """अगला सवाल भेजो"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    q_index = int(query.data.split("_")[1])
    await send_question(update, context, user_id, q_index)


async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """फाइनल रिजल्ट दिखाओ"""
    score = user_scores.get(user_id, 0)
    total = len(QUIZZES)
    percent = (score / total) * 100

    if percent >= 80:
        grade = "🌟 बहुत बढ़िया!"
    elif percent >= 60:
        grade = "👍 अच्छा है!"
    elif percent >= 40:
        grade = "😐 ठीक है"
    else:
        grade = "😅 फिर से कोशिश करो"

    text = f"""
🏆 **क्विज़ खत्म!** 🏆

━━━━━━━━━━━━━━━
📊 स्कोर: **{score}/{total}**
📈 प्रतिशत: **{percent:.0f}%**
🏅 ग्रेड: **{grade}**
━━━━━━━━━━━━━━━

🔄 दोबारा खेलने के लिए /quiz दबाओ!
"""
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.callback_query.message.edit_text(text, parse_mode="Markdown")


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """स्कोर दिखाओ"""
    user_id = update.effective_user.id
    s = user_scores.get(user_id, 0)
    await update.message.reply_text(f"📊 **तुम्हारा स्कोर:** {s}/{len(QUIZZES)}", parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """स्कोर रीसेट"""
    user_id = update.effective_user.id
    user_scores[user_id] = 0
    user_current_q[user_id] = 0
    await update.message.reply_text("🔄 स्कोर रीसेट हो गया!\n👉 /quiz दबाओ नया क्विज़ शुरू करने के लिए")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """हेल्प"""
    text = """
📖 **हेल्प - Quiz Bot**

🎮 **कमांड्स:**
• /start - बॉट शुरू करो
• /quiz - क्विज़ शुरू करो
• /score - स्कोर देखो
• /reset - स्कोर रीसेट करो
• /help - ये मैसेज

🎯 **कैसे खेलना है:**
1. /quiz दबाओ
2. 4 ऑप्शन आएंगे - एक सही चुनो
3. हर जवाब के बाद वजह बताएंगे
4. "अगला सवाल" दबाओ आगे बढ़ने के लिए
5. आखिर में फाइनल रिजल्ट दिखेगा
"""
    await update.message.reply_text(text, parse_mode="Markdown")


def main():
    """बॉट चलाने का मुख्य फंक्शन"""
    TOKEN = os.environ.get("BOT_TOKEN")

    if not TOKEN:
        print("❌ BOT_TOKEN नहीं मिला!")
        print("💡 Railway में BOT_TOKEN variable जोड़ो")
        return

    print("🚀 Quiz Bot शुरू हो रहा है...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern=r"^ans_"))
    app.add_handler(CallbackQueryHandler(next_question, pattern=r"^next_"))

    print("✅ बॉट चल रहा है!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()