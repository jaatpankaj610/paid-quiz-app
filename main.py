from flask import Flask, render_template, request, jsonify
import os
import random
import time
import logging

# लॉगिंग सेटअप
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secure_key_2025'  # सुरक्षित पासवर्ड
USERS_FILE = "users.json"
PENDING_PAYMENTS_FILE = "pending_payments.json"
AMAZON_PAY_QR_LINK = "upi://pay?pa=your-upi-id@upi&pn=YourName&mc=0000&tid=your-transaction-id&tn=Payment for Quiz"

# फोल्डर बनाना
def ensure_folders_exist():
    if not os.path.exists('payment_proofs'):
        os.makedirs('payment_proofs')
        logger.info("payment_proofs फोल्डर बनाया गया")

# प्रश्न लोड करना
def load_questions():
    try:
        with open("question.txt", "r", encoding="utf-8") as f:
            lines = f.read().split("\n\n")
            questions = []
            for block in lines:
                if not block.strip():
                    continue
                parts = block.split("\n")
                if len(parts) < 2:
                    continue
                q = parts[0].strip()
                options = [p.strip("*") for p in parts[1:]]
                correct_index = next((i for i, p in enumerate(parts[1:]) if p.startswith("*")), None)
                if correct_index is not None:
                    questions.append({"question": q, "options": options, "answer": correct_index})
            logger.info(f"{len(questions)} प्रश्न लोड हुए")
            return questions
    except Exception as e:
        logger.error(f"प्रश्न लोड त्रुटि: {e}")
        return []

# यूजर डेटा
def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return eval(f.read())
        return {}
    except Exception as e:
        logger.error(f"यूजर डेटा त्रुटि: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, 'w') as f:
            f.write(str(users))
        logger.info("यूजर डेटा सेव हुआ")
    except Exception as e:
        logger.error(f"यूजर डेटा सेव त्रुटि: {e}")

def load_pending_payments():
    try:
        if os.path.exists(PENDING_PAYMENTS_FILE):
            with open(PENDING_PAYMENTS_FILE, 'r') as f:
                return eval(f.read())
        return {}
    except Exception as e:
        logger.error(f"पेंडिंग पेमेंट त्रुटि: {e}")
        return {}

def save_pending_payments(payments):
    try:
        with open(PENDING_PAYMENTS_FILE, 'w') as f:
            f.write(str(payments))
        logger.info("पेंडिंग पेमेंट्स सेव हुए")
    except Exception as e:
        logger.error(f"पेंडिंग पेमेंट्स सेव त्रुटि: {e}")

# रूट्स
@app.route("/")
def home():
    ensure_folders_exist()
    logger.info("होम पेज लोड")
    return render_template("index.html", qr_code_data="https://via.placeholder.com/150", AMAZON_PAY_QR_LINK=AMAZON_PAY_QR_LINK)

@app.route("/submit_payment", methods=['POST'])
def submit_payment():
    logger.info("पेमेंट सबमिशन रिक्वेस्ट")
    user_id = request.form.get('user_id')
    amount = request.form.get('amount')
    if user_id and amount:
        transaction_id = f"TXN{int(time.time())}{random.randint(1000, 9999)}"
        pending_payments = load_pending_payments()
        pending_payments[f"{user_id}_{transaction_id}"] = {
            "user_id": user_id,
            "amount": amount,
            "status": "pending",
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_pending_payments(pending_payments)
        logger.info(f"पेमेंट सबमिट: {user_id}, राशि: {amount}")
        return jsonify({"success": True, "message": "पेमेंट सफलतापूर्वक सबमिट हो गया!"})
    return jsonify({"success": False, "message": "कृपया सभी डेटा भरें!"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5000)))
