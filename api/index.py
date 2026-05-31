import os
import sys
import traceback
import telebot
from groq import Groq
from flask import Flask, request

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

app = Flask(__name__)

# Log startup
print(f"Starting bot... BOT_TOKEN={'set' if BOT_TOKEN else 'MISSING'}, GROQ_API_KEY={'set' if GROQ_API_KEY else 'MISSING'}", flush=True)

try:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    client = Groq(api_key=GROQ_API_KEY)
    bot_ready = True
    print("Bot initialized successfully", flush=True)
except Exception as e:
    bot_ready = False
    init_error = str(e)
    print(f"Bot init failed: {init_error}", flush=True)

if bot_ready:
    @bot.message_handler(commands=['start'])
    def start(message):
        bot.reply_to(message, "Halo! Saya asisten AI Fredi. Tanya apa saja!")

    @bot.message_handler(func=lambda message: True)
    def handle(message):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": message.text}],
                max_tokens=1000
            )
            bot.reply_to(message, response.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, "Maaf ada error, coba lagi!")

@app.route('/', methods=['POST'])
@app.route('/api/', methods=['POST'])
def webhook():
    if not bot_ready:
        return f"Bot not ready: {init_error}", 500
    try:
        body = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return 'ok', 200
    except Exception as e:
        traceback.print_exc()
        return f"Error: {str(e)}", 500

@app.route('/', methods=['GET'])
@app.route('/api/', methods=['GET'])
def index():
    status = "ready" if bot_ready else "error"
    return f'Telegram AI Bot is running! Status: {status}', 200 if bot_ready else 500
