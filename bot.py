import os
import random
import requests
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# लॉगिंग सेटअप
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = ""
GEMINI_API_KEY = "AQ.Ab8RN6I8NtXy-q7H3WQPXGnJrpbTXsXrwLjA1Vs80h9YCxkccw"

# Gemini क्लाइंट
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# यूजर मेमोरी
USER_SEEN_FACTS = {}

# --- Render Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    # Render हमेशा PORT नाम का एनवायरनमेंट वेरिएबल देता है, डिफ़ॉल्ट 8080 रखेंगे
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Health check server started on port {port}")
    server.serve_forever()

# --- Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    USER_SEEN_FACTS[user_id] = []
    await update.message.reply_text(
        "👋 राम राम भाई! आपका स्मार्ट फैक्ट-टू-क्विज बोट तैयार है।\n\n"
        "⏱️ शुरू करने के लिए `/test` या `/startquiz` कमांड दबाएं।"
    )

async def generate_live_quiz(facts_list):
    prompt = f"""
    तुम्हें नीचे दिए गए तथ्यों (Facts) का उपयोग करके 20 बेहतरीन परीक्षा-उपयोगी (Exam-Oriented) बहुविकल्पीय प्रश्न (MCQs) तैयार करने हैं।
    प्रत्येक फैक्ट से एक प्रश्न बनाना है।
    
    सख्त नियम:
    1. उच्चारण शुद्ध रखने के लिए हिंदी अक्षर 'ड़' की जगह हमेशा 'ड' का प्रयोग करें (जैसे 'बड़ा' की जगह 'बडा', 'पकड़' की जगह 'पकड').
    2. आउटपुट केवल और केवल एक वैध JSON Array होना चाहिए, जिसमें कोई अतिरिक्त टेक्स्ट या ```json ``` ब्लॉक न हो।
    
    JSON का फॉर्मेट:
    [
      {{
        "question_text": "प्रश्न यहाँ...",
        "options": ["A) विकल्प 1", "B) विकल्प 2", "C) विकल्प 3", "D) विकल्प 4"],
        "correct_option": "A"
      }}
    ]

    तथ्य (Facts) यहाँ हैं:
    {json.dumps(facts_list, ensure_ascii=False)}
    """
    response = ai_client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt,
    )
    return json.loads(response.text.strip())

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    message = update.message
    await message.reply_text("🔄 AI से नए सवाल बनवा रहा हूँ, कृपया 10-15 सेकंड रुकें...")

    try:
        res = requests.get("https://raw.githubusercontent.com/jaatpankaj610/paid-quiz-app/refs/heads/main/facts.json")
        all_facts = res.json()
        
        seen_list = USER_SEEN_FACTS.get(user_id, [])
        unseen_facts = [f for f in all_facts if f not in seen_list]
        
        if len(unseen_facts) < 20:
            unseen_facts = all_facts
            seen_list = []
            await message.reply_text("🔄 progress reset हो रही है, दोबारा नए सिरे से सवाल आएंगे।")

        selected_facts = random.sample(unseen_facts, min(20, len(unseen_facts)))
        seen_list.extend(selected_facts)
        USER_SEEN_FACTS[user_id] = seen_list

        quiz_data = await generate_live_quiz(selected_facts)
        
        context.user_data['quiz_questions'] = quiz_data
        context.user_data['current_index'] = 0
        context.user_data['score'] = 0
        
        await send_next_question(message, context)
    except Exception as e:
        await message.reply_text(f"❌ गड़बड़ हो गई भाई! Error: {str(e)[:100]}")

async def send_next_question(message, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data.get('quiz_questions', [])
    index = context.user_data.get('current_index', 0)
    
    if index >= len(questions):
        score = context.user_data.get('score', 0)
        await message.reply_text(f"🏁 **टेस्ट समाप्त भाई!**\n\n📊 आपका स्कोर: {score}/{len(questions)}\n\nअगले नए सवालों के लिए फिर से `/test` दबाएं।")
        return

    q = questions[index]
    text = f"📝 **प्रश्न {index + 1}:** {q['question_text']}\n\n"
    for opt in q['options']:
        text += f"{opt}\n"

    keyboard = [
        [InlineKeyboardButton("A", callback_data=f"ans_A_{q['correct_option']}"),
         InlineKeyboardButton("B", callback_data=f"ans_B_{q['correct_option']}")],
        [InlineKeyboardButton("C", callback_data=f"ans_C_{q['correct_option']}"),
         InlineKeyboardButton("D", callback_data=f"ans_D_{q['correct_option']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(message, 'edit_text'):
        await message.edit_text(text, reply_markup=reply_markup)
    else:
        await message.reply_text(text, reply_markup=reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    user_choice = data[1]
    correct_choice = data[2]
    
    index = context.user_data.get('current_index', 0)
    questions = context.user_data.get('quiz_questions', [])
    q = questions[index]
    
    if user_choice == correct_choice:
        context.user_data['score'] += 1
        result_text = f"✅ **सही उत्तर भाई!**\n\n"
    else:
        result_text = f"❌ **गलत जवाब!**\n\n👉 सही उत्तर **{correct_choice}** था।\n\n"
        
    full_text = f"📝 **प्रश्न {index + 1}:** {q['question_text']}\n"
    for opt in q['options']:
        full_text += f"\n{opt}"
    full_text += f"\n\n--- \n{result_text}"
    
    keyboard = [[InlineKeyboardButton("अगला प्रश्न ➡️", callback_data="next_question")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=full_text, reply_markup=reply_markup)

async def next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['current_index'] += 1
    await send_next_question(query.message, context)

def main():
    # बोट शुरू होने से ठीक पहले बैकग्राउंड में हेल्थ चेक सर्वर चालू करना ताकि Render खुश रहे
    threading.Thread(target=run_health_check_server, daemon=True).start()

    # बोट एप्लीकेशन सेटअप
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("test", start_test))
    application.add_handler(CommandHandler("startquiz", start_test))
    application.add_handler(CallbackQueryHandler(next_callback, pattern="^next_question$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^ans_"))
    
    logger.info("Starting Telegram Bot Polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
