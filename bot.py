import os
import io
import base64
import telebot
from groq import Groq
from duckduckgo_search import DDGS

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

SEARCH_TRIGGERS = ['cari', 'search', 'google', 'latest', 'terbaru', 'berita', 'news', 'update', 'terkini', 'hari ini']

def web_search(query, max_results=5):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        return []

def should_search(text):
    t = text.lower().strip()
    if t.startswith('/search') or t.startswith('!cari') or t.startswith('cari '):
        return True
    return any(trigger in t for trigger in SEARCH_TRIGGERS)

def format_results(results):
    if not results:
        return ""
    out = "\n\n--- HASIL PENCARIAN WEB ---\n"
    for i, r in enumerate(results[:5], 1):
        out += f"{i}. {r.get('title', '')}\n{r.get('body', '')}\n{r.get('href', '')}\n\n"
    return out

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message,
        "Halo! Saya asisten AI Fredi dengan kemampuan:\n\n"
        "🤖 Tanya apa saja, AI akan menjawab\n"
        "🌐 /search <query> atau ketik 'cari ...' untuk info terbaru\n"
        "🖼️ Kirim gambar untuk analisis & baca teks\n\n"
        "Contoh: /search harga emas hari ini")

@bot.message_handler(commands=['search'])
def search_command(message):
    q = message.text.replace('/search', '', 1).strip()
    if not q:
        bot.reply_to(message, "Gunakan: /search <query>")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    results = web_search(q)
    ctx = format_results(results)
    prompt = f"Pertanyaan: {q}\n{ctx}\nJawab berdasarkan hasil pencarian di atas. Jika kosong, gunakan pengetahuanmu."
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500)
    bot.reply_to(message, resp.choices[0].message.content)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64 = base64.b64encode(downloaded).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{b64}"

        prompt = message.caption or "Baca dan analisis semua teks yang ada di gambar ini. Jelaskan isinya secara detail."
        resp = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]}],
            max_tokens=2000)
        bot.reply_to(message, resp.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"Maaf, gagal memproses gambar: {str(e)}")

@bot.message_handler(func=lambda m: True)
def handle(message):
    text = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    if should_search(text):
        q = text
        for p in ['/search', '!cari', 'cari ']:
            if text.lower().startswith(p):
                q = text[len(p):].strip()
                break
        results = web_search(q)
        ctx = format_results(results)
        prompt = f"Pertanyaan: {q}\n{ctx}\nJawab berdasarkan hasil pencarian di atas. Jika kosong, gunakan pengetahuanmu."
    else:
        prompt = text
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500)
    bot.reply_to(message, resp.choices[0].message.content)

bot.infinity_polling()
