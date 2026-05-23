import os
import telebot
from groq import Groq

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Halo! Saya asisten AI Fredi. Tanya apa saja!")

@bot.message_handler(func=lambda message: True)
def handle(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": message.text}],
            max_tokens=1000
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, "Maaf ada error, coba lagi!")

bot.infinity_polling()
