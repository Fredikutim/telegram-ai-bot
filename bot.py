import os
import io
import base64
import telebot
from groq import Groq
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else InferenceClient()

current_model = "groq"

HF_TEXT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_IMAGE_MODEL = "Salesforce/blip-image-captioning-base"

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

def ask_groq(prompt, max_tokens=1500):
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens)
    return resp.choices[0].message.content

def ask_groq_vision(prompt, data_url):
    resp = groq_client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        max_tokens=2000)
    return resp.choices[0].message.content

def ask_hf(prompt, max_tokens=1500):
    return hf_client.text_generation(prompt, model=HF_TEXT_MODEL, max_new_tokens=max_tokens, temperature=0.7)

def ask_hf_vision(prompt, image_bytes):
    result = hf_client.image_to_text(image_bytes, model=HF_IMAGE_MODEL)
    return f"[HF Image Caption]\n{result}"

@bot.message_handler(commands=['start'])
def start(message):
    provider = "Groq" if current_model == "groq" else f"Hugging Face ({HF_TEXT_MODEL})"
    bot.reply_to(message,
        f"Halo! Saya asisten AI Fredi.\n\n"
        f"🤖 AI aktif: {provider}\n"
        f"🌐 /search <query> atau 'cari ...' untuk info terbaru\n"
        f"🖼️ Kirim gambar untuk analisis\n"
        f"⚙️ /model untuk ganti penyedia AI")

@bot.message_handler(commands=['model'])
def model_info(message):
    provider = "Groq (Llama 3.3 70B)" if current_model == "groq" else f"Hugging Face ({HF_TEXT_MODEL})"
    bot.reply_to(message,
        f"Penyedia AI: {provider}\n"
        f"/setmodel groq - Groq\n"
        f"/setmodel hf - Hugging Face")

@bot.message_handler(commands=['setmodel'])
def set_model(message):
    global current_model
    choice = message.text.replace('/setmodel', '', 1).strip().lower()
    if choice == 'groq':
        current_model = 'groq'
        bot.reply_to(message, "✅ Beralih ke Groq")
    elif choice in ('hf', 'huggingface'):
        current_model = 'hf'
        bot.reply_to(message, f"✅ Beralih ke Hugging Face ({HF_TEXT_MODEL})")
    else:
        bot.reply_to(message, "Gunakan: /setmodel groq atau /setmodel hf")

@bot.message_handler(commands=['search'])
def search_command(message):
    q = message.text.replace('/search', '', 1).strip()
    if not q:
        bot.reply_to(message, "Gunakan: /search <query>")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    results = web_search(q)
    ctx = format_results(results)
    prompt = f"Pertanyaan: {q}\n{ctx}\nJawab berdasarkan hasil pencarian di atas."
    try:
        reply = ask_groq(prompt) if current_model == 'groq' else ask_hf(prompt)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64 = base64.b64encode(downloaded).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{b64}"
        prompt = message.caption or "Baca dan analisis semua teks yang ada di gambar ini."
        try:
            reply = ask_groq_vision(prompt, data_url) if current_model == 'groq' else ask_hf_vision(prompt, downloaded)
        except Exception:
            reply = ask_hf_vision(prompt, downloaded) if current_model == 'groq' else ask_groq_vision(prompt, data_url)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Gagal: {str(e)}")

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
        prompt = f"Pertanyaan: {q}\n{ctx}\nJawab berdasarkan hasil pencarian di atas."
    else:
        prompt = text
    try:
        reply = ask_groq(prompt) if current_model == 'groq' else ask_hf(prompt)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

bot.infinity_polling()
