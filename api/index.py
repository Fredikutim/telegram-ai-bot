import os
import sys
import json
import traceback
import telebot
from groq import Groq
from flask import Flask, request, Response

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

app = Flask(__name__)

print(f"Startup: BOT_TOKEN={'OK' if BOT_TOKEN else 'MISS'}", flush=True)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
client = Groq(api_key=GROQ_API_KEY)
print("Bot OK", flush=True)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Halo! Saya asisten AI Fredi. Tanya apa saja!")

@bot.message_handler(func=lambda message: True)
def handle(message):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": message.text}],
        max_tokens=1000
    )
    bot.reply_to(message, response.choices[0].message.content)

@app.route('/', methods=['GET'])
def index():
    return 'Telegram AI Bot is running!', 200

@app.route('/', methods=['POST'])
def webhook():
    try:
        body = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return ('ok', 200)
    except Exception as e:
        err = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(err, flush=True)
        return (err, 200)
