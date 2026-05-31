import os
import telebot
from groq import Groq
from flask import Flask, request

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
client = Groq(api_key=GROQ_API_KEY)
app = Flask(__name__)

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
    body = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(body)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/', methods=['GET'])
@app.route('/api/', methods=['GET'])
def index():
    return 'Telegram AI Bot is running!', 200
