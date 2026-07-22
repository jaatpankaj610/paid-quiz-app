import os
import sys
import logging
import threading
import asyncio
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# 1. लॉगिंग
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 2. क्रेडेंशियल्स
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"AI Setup Error: {e}")

# 3. हेल्थ सर्वर (Render के लिए)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Quiz Bot is Online")
    def log_message(self, format, *args): return

def run_health_server():
    httpd = HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), HealthCheckHandler)
    httpd.serve_forever()

# --- 4. AI QUIZ GENERATION ---

def load_user_facts():
    try:
        if os.path.exists("facts.json"):
            with open("facts.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return "\n".join(data) if isinstance(data, list) else str(data)
    except: pass
    return "भारत का इतिहास और सामान्य ज्ञान।"

async def generate_quiz_ai():
    user_facts = load_user_facts()
    
    # अब यहाँ 20 सवाल माँगे गए हैं
    prompt = f"""
    तुम्हें नीचे दिए गए तथ्यों (Facts) का उपयोग करके बिल्कुल 20 बेहतरीन GK MCQs तैयार करने हैं।
    तथ्य: {user_facts}
    
    नियम:
    1. 'ड़' की जगह हमेशा 'ड' का प्रयोग करें।
    2. आउटपुट केवल एक शुद्ध JSON Array होना चाहिए।
    3. बिल्कुल 20 सवाल ही दें।
    Format: [{{ "question": "...", "options": ["A", "B", "C", "D"], "answer": 0 }}]
    """
    try:
        response = ai_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        # JSON निकालने का पक्का तरीका
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        logger.error(f"AI Generation Error: {e}")
        return None

# --- 5. BOT HANDLERS ---

# अब /start ही मेन कमांड है जो सीधा 20 सवाल शुरू करेगा
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # अगर क्विज़ चल रहा है या सवाल बन रहे हैं, तो कुछ मत करो (इग्नोर कर दो)
    if context.user_data.get('is_generating') or context.user_data.get('quiz'):
        return 

    context.user_data['is_generating'] = True
    msg = await update.message.reply_text("⏳ AI 20 सवाल तैयार कर रहा है... इसमें 20-30 सेकंड लग सकते हैं।")
    
    quiz_data = await generate_quiz_ai()
    
    context.user_data['is_generating'] = False # UNLOCK
    if not quiz_data:
        await msg.edit_text("❌ AI अभी बिजी है। कृपया 1 मिनट बाद फिर से /start लिखें।")
        return

    context.user_data.update({'quiz': quiz_data, 'current_q': 0, 'score': 0})
    await show_question(update, context, msg)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, message_obj=None):
    idx = context.user_data['current_q']
    q = context.user_data['quiz'][idx]
    buttons = [[InlineKeyboardButton(opt, callback_data=str(i))] for i, opt in enumerate(q['options'])]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # यहाँ 10 की जगह 20 कर दिया गया है
    text = f"❓ **सवाल {idx+1}/20**\n\n{q['question']}"
    
    if message_obj: 
        await message_obj.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else: 
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if 'quiz' not in context.user_data: return
    await query.answer()
    
    user_ans = int(query.data)
    idx = context.user_data['current_q']
    quiz = context.user_data['quiz']
    correct = quiz[idx]['answer']

    res = "✅ सही!" if user_ans == correct else f"❌ गलत! सही: {quiz[idx]['options'][correct]}"
    if user_ans == correct: context.user_data['score'] += 1

    context.user_data['current_q'] += 1
    
    # अगर अभी 20 सवाल पूरे नहीं हुए हैं
    if context.user_data['current_q'] < len(quiz):
        await query.message.edit_text(f"{res}\n\nअगला सवाल आ रहा है...")
        await asyncio.sleep(1)
        await show_question(update, context)
    else:
        # 20वें सवाल के बाद डायरेक्ट स्कोर स्क्रीन
        score = context.user_data['score']
        # क्विज़ डेटा हटा दिया जाता है ताकि यूज़र दोबारा /start भेज सके
        context.user_data.pop('quiz', None)
        context.user_data.pop('current_q', None)
        context.user_data.pop('score', None)
        
        await query.message.edit_text(
            f"🏆 क्विज़ पूरा हो गया!\n\n🥇 आपका स्कोर: {score}/20\n\nनया टेस्ट शुरू करने के लिए /start दबाएँ।", 
            parse_mode='Markdown'
        )

# यह हैंडलर किसी भी दूसरे मैसेज या कमांड को बीच में आने से रोकेगा
async def ignore_all_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # अगर क्विज़ चल रहा है या बन रहा है, तो यूज़र का मैसेज इग्नोर कर दो (कोई रिप्लाई नहीं)
    if context.user_data.get('is_generating') or context.user_data.get('quiz'):
        return
    # अगर कोई बेवजह कुछ टाइप करे जब क्विज़ चल नहीं रहा
    await update.message.reply_text("कृपया क्विज़ शुरू करने के लिए /start भेजें।")

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # कमांड्स और बटन्स रजिस्टर करना
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_answer))
    
    # सबसे नीचे इसे लगाया गया है ताकि अगर कोई टेक्स्ट/कमांड आए और ऊपर किसी हैंडलर ने हैंडल नहीं किया, तो यह इग्नोर कर दे
    app.add_handler(MessageHandler(filters.ALL, ignore_all_other_messages))
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    try:
        asyncio.run(run_bot())
    except: sys.exit(1)
