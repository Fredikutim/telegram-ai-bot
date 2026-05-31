import os
import io
import base64
import traceback
import telebot
from groq import Groq
from flask import Flask, request
from duckduckgo_search import DDGS
from huggingface_hub import InferenceClient

BOT_TOKEN = os.environ.get('BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
HF_TOKEN = os.environ.get('HF_TOKEN')

app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
groq_client = Groq(api_key=GROQ_API_KEY)
hf_client = InferenceClient(token=HF_TOKEN) if HF_TOKEN else InferenceClient()

current_model = "groq"
HF_TEXT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_IMAGE_MODEL = "Salesforce/blip-image-captioning-base"
HF_TTI_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_I2I_MODEL = "timbrooks/instruct-pix2pix"

SEARCH_TRIGGERS = ['cari', 'search', 'google', 'latest', 'terbaru', 'berita', 'news', 'update', 'terkini', 'hari ini']
GEN_TRIGGERS = ['gambar', 'buat', 'generate', 'lukis', 'foto', 'gambar ', 'buatkan']

def web_search(query, max_results=5):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results
    except Exception as e:
        print(f"Search error: {e}", flush=True)
        return []

def should_search(text):
    t = text.lower().strip()
    if t.startswith('/search') or t.startswith('!cari') or t.startswith('cari '):
        return True
    return any(trigger in t for trigger in SEARCH_TRIGGERS)

def should_generate(text):
    t = text.lower().strip()
    if text.startswith('/generate'):
        return True
    return any(text.lower().startswith(g) for g in ['gambar ', 'buat ', 'buatkan ', 'gambar:', 'buat:'])

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

def ask_groq_vision(prompt, data_url, max_tokens=2000):
    resp = groq_client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": data_url}}]}],
        max_tokens=max_tokens)
    return resp.choices[0].message.content

def ask_hf(prompt, max_tokens=1500):
    return hf_client.text_generation(prompt, model=HF_TEXT_MODEL, max_new_tokens=max_tokens, temperature=0.7)

def ask_hf_vision(prompt, image_bytes):
    result = hf_client.image_to_text(image_bytes, model=HF_IMAGE_MODEL)
    return f"[HF Image Caption]\n{result}"

def hf_generate_image(prompt):
    image = hf_client.text_to_image(prompt, model=HF_TTI_MODEL)
    buf = io.BytesIO()
    image.save(buf, format='JPEG')
    buf.seek(0)
    return buf

def hf_edit_image(image_bytes, prompt):
    result = hf_client.image_to_image(image_bytes, prompt=prompt, model=HF_I2I_MODEL)
    buf = io.BytesIO()
    result.save(buf, format='JPEG')
    buf.seek(0)
    return buf

def send_menu(chat_id, text):
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("/generate"),
        KeyboardButton("/search"),
        KeyboardButton("/model"),
        KeyboardButton("/help"),
        KeyboardButton("/setmodel groq"),
        KeyboardButton("/setmodel hf"),
    )
    bot.send_message(chat_id, text, reply_markup=markup)

MENU_TEXT = (
    "📋 MENU BOT ASISTEN AI FREDI\n\n"
    "💬 Tanya apa saja — AI akan menjawab\n\n"
    "🎨 Buat gambar:\n"
    "  /generate <deskripsi>\n"
    "  atau ketik: gambar <deskripsi>\n\n"
    "✏️ Edit gambar — kirim foto dg caption:\n"
    "  edit: <instruksi>\n\n"
    "🌐 Cari info terbaru:\n"
    "  /search <query>\n"
    "  atau ketik: cari <query>\n\n"
    "🖼️ Kirim gambar — AI baca & analisis teks\n\n"
    "⚙️ Pengaturan AI:\n"
    "  /model — lihat AI aktif saat ini\n"
    "  /setmodel groq — Groq (rekomendasi)\n"
    "  /setmodel hf — Hugging Face (gratis)\n\n"
    "📌 Contoh: /generate kucing terbang di luar angkasa"
)

@bot.message_handler(commands=['start', 'menu', 'help'])
def start(message):
    provider = "Groq (Llama 3.3 70B)" if current_model == "groq" else f"Hugging Face ({HF_TEXT_MODEL})"
    text = f"🤖 Asisten AI Fredi — AI aktif: {provider}\n\n{MENU_TEXT}"
    send_menu(message.chat.id, text)

@bot.message_handler(commands=['model'])
def model_info(message):
    provider = "Groq (Llama 3.3 70B)" if current_model == "groq" else f"Hugging Face ({HF_TEXT_MODEL})"
    vision = "Groq Vision (Llama 3.2 90B)" if current_model == "groq" else f"Hugging Face ({HF_IMAGE_MODEL})"
    tti = HF_TTI_MODEL
    text = (
        f"🤖 Penyedia AI: {provider}\n"
        f"🖼️ Analisis gambar: {vision}\n"
        f"🎨 Generate gambar: {tti}\n\n"
        f"Gunakan /help untuk menu lengkap"
    )
    send_menu(message.chat.id, text)

@bot.message_handler(commands=['setmodel'])
def set_model(message):
    global current_model
    choice = message.text.replace('/setmodel', '', 1).strip().lower()
    if choice == 'groq':
        current_model = 'groq'
        send_menu(message.chat.id, "✅ Beralih ke Groq (Llama 3.3 70B)")
    elif choice in ('hf', 'huggingface'):
        current_model = 'hf'
        send_menu(message.chat.id, f"✅ Beralih ke Hugging Face ({HF_TEXT_MODEL})")
    else:
        send_menu(message.chat.id, "Gunakan: /setmodel groq atau /setmodel hf")

@bot.message_handler(commands=['generate'])
def generate_command(message):
    prompt = message.text.replace('/generate', '', 1).strip()
    if not prompt:
        send_menu(message.chat.id, "Gunakan: /generate <deskripsi>\nContoh: /generate kucing terbang pakai jetpack")
        return
    bot.send_chat_action(message.chat.id, 'upload_photo')
    msg = bot.reply_to(message, "🎨 Sedang membuat gambar... mohon tunggu ~20 detik")
    try:
        buf = hf_generate_image(prompt)
        bot.delete_message(message.chat.id, msg.message_id)
        bot.send_photo(message.chat.id, buf, caption=f"🎨 {prompt}")
    except Exception as e:
        bot.edit_message_text(f"Gagal: {str(e)}", message.chat.id, msg.message_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        b64 = base64.b64encode(downloaded).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{b64}"
        caption = (message.caption or "").strip()

        if caption.lower().startswith("edit:"):
            prompt = caption[5:].strip()
            if not prompt:
                bot.reply_to(message, "Gunakan: edit: <instruksi>\nContoh caption: edit: jadikan style anime")
                return
            msg = bot.reply_to(message, "✏️ Sedang mengedit gambar... mohon tunggu")
            try:
                buf = hf_edit_image(downloaded, prompt)
                bot.delete_message(message.chat.id, msg.message_id)
                bot.send_photo(message.chat.id, buf, caption=f"✏️ {prompt}")
            except Exception as e:
                bot.edit_message_text(f"Gagal edit: {str(e)}", message.chat.id, msg.message_id)
            return

        prompt = caption or "Baca dan analisis semua teks yang ada di gambar ini. Jelaskan isinya secara detail."
        try:
            reply = ask_groq_vision(prompt, data_url)
        except Exception:
            reply = ask_hf_vision(prompt, downloaded)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Maaf, gagal memproses gambar: {str(e)}")

@bot.message_handler(commands=['search'])
def search_command(message):
    q = message.text.replace('/search', '', 1).strip()
    if not q:
        send_menu(message.chat.id, "Gunakan: /search <query>\nContoh: /search berita terbaru 2026")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    results = web_search(q)
    ctx = format_results(results)
    prompt = f"Pertanyaan: {q}\n{ctx}\nJawab berdasarkan hasil pencarian di atas. Jika kosong, gunakan pengetahuanmu."
    try:
        reply = ask_groq(prompt) if current_model == 'groq' else ask_hf(prompt)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}. Coba ganti model dengan /setmodel")

@bot.message_handler(func=lambda m: True)
def handle(message):
    text = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    if should_generate(text):
        for p in ['/generate', 'gambar ', 'buat ', 'buatkan ', 'gambar:', 'buat:']:
            if text.lower().startswith(p):
                prompt = text[len(p):].strip()
                break
        if prompt:
            msg = bot.reply_to(message, "🎨 Sedang membuat gambar... mohon tunggu ~20 detik")
            try:
                buf = hf_generate_image(prompt)
                bot.delete_message(message.chat.id, msg.message_id)
                bot.send_photo(message.chat.id, buf, caption=f"🎨 {prompt}")
            except Exception as e:
                bot.edit_message_text(f"Gagal: {str(e)}", message.chat.id, msg.message_id)
            return
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
    try:
        reply = ask_groq(prompt) if current_model == 'groq' else ask_hf(prompt)
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}. Coba ganti model dengan /setmodel")

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
