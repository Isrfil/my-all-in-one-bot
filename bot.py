import os, qrcode, asyncio, httpx
from pypdf import PdfReader, PdfWriter
from yt_dlp import YoutubeDL
from PIL import Image
from gtts import gTTS
import pyshorteners
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- Flask Server (বটকে ২৪ ঘণ্টা সচল রাখতে) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "Professional Bot is Running!"
def run(): app_web.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320

# ডেটা স্টোর
user_images = {}
pdf_edit_files = {}

# --- মেইন কিবোর্ড (স্থায়ী) ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 ভিডিও ডাউনলোড"), KeyboardButton("📄 PDF এডিটর")],
        [KeyboardButton("🖼 Image to PDF"), KeyboardButton("🗣 Text to Speech")],
        [KeyboardButton("🔍 QR Code"), KeyboardButton("🔗 Link Shorten")],
        [KeyboardButton("👤 প্রোফাইল")]
    ], resize_keyboard=True, is_persistent=True)

# --- ভিডিও ডাউনলোডার মেনু ---
def video_download_menu():
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data='v_info'), InlineKeyboardButton("📘 Facebook", callback_data='v_info')],
        [InlineKeyboardButton("🎥 YouTube", callback_data='v_info'), InlineKeyboardButton("🎵 TikTok", callback_data='v_info')],
        [InlineKeyboardButton("🐦 Twitter (X)", callback_data='v_info')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- স্টার্ট কমান্ড ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"🔥 স্বাগতম {update.effective_user.first_name}!\nনিচের মেনু থেকে আপনার সার্ভিসটি বেছে নিন।",
        reply_markup=main_keyboard()
    )

# --- টেক্সট হ্যান্ডলার ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    # বাটন ক্লিক করলে রিসেট
    if text in ["📱 ভিডিও ডাউনলোড", "📄 PDF এডিটর", "🖼 Image to PDF", "🗣 Text to Speech", "🔍 QR Code", "🔗 Link Shorten"]:
        context.user_data.clear()

    # ১. ভিডিও ডাউনলোড সেকশন
    if text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 **ভিডিও ডাউনলোডার সক্রিয়!**\nযেকোনো সোশ্যাল মিডিয়া লিংক এখানে পাঠান।", reply_markup=video_download_menu())

    # ২. পিডিএফ এডিটর সেকশন
    elif text == "📄 PDF এডিটর":
        await update.message.reply_text("📂 একটি **PDF ফাইল** পাঠান। এরপর আপনি সেটি Rotate বা Merge করতে পারবেন।")

    # ৩. ইমেজ টু পিডিএফ সেকশন
    elif text == "🖼 Image to PDF":
        user_images[user_id] = []
        keyboard = [[InlineKeyboardButton("✅ Convert to PDF", callback_data='convert_img_pdf')]]
        await update.message.reply_text("📥 একে একে ছবি পাঠান। শেষ হলে নিচের বাটনে ক্লিক করুন।", reply_markup=InlineKeyboardMarkup(keyboard))

    # ৪. টেক্সট টু স্পিচ সেকশন
    elif text == "🗣 Text to Speech":
        context.user_data['state'] = 'TTS_TEXT'
        await update.message.reply_text("📝 যে লেখাটি ভয়েস করতে চান তা লিখে পাঠান:")

    elif state == 'TTS_TEXT':
        context.user_data['tts_text'] = text
        btns = [[InlineKeyboardButton("👨 Male (পুরুষ)", callback_data='tts_male'), 
                 InlineKeyboardButton("👩 Female (নারী)", callback_data='tts_female')]]
        await update.message.reply_text("🎙 কোন ভয়েসটি চান?", reply_markup=InlineKeyboardMarkup(btns))

    # ৫. কিউআর ও শর্টেনার
    elif text == "🔍 QR Code":
        context.user_data['state'] = 'QR'
        await update.message.reply_text("লিংক বা টেক্সট পাঠান:")
    elif state == 'QR':
        path = f"qr_{user_id}.png"
        qrcode.make(text).save(path)
        await update.message.reply_photo(photo=open(path, 'rb'), caption="✅ QR Code তৈরি সম্পন্ন!")
        os.remove(path)
        context.user_data.clear()

    # লিংক শনাক্তকরণ (ভিডিওর জন্য)
    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎥 Download Video", callback_data='dl_v'), 
                 InlineKeyboardButton("🎵 Download MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে! কি ফরমেটে ডাউনলোড করতে চান?", reply_markup=InlineKeyboardMarkup(btns))

# --- ফাইল হ্যান্ডলার (Photo & PDF) ---
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ছবি হ্যান্ডলার
    if update.message.photo and user_id in user_images:
        photo = await update.message.photo[-1].get_file()
        path = f"img_{user_id}_{len(user_images[user_id])}.jpg"
        await photo.download_to_drive(path)
        user_images[user_id].append(path)
        await update.message.reply_text(f"✅ {len(user_images[user_id])} নং ছবি যুক্ত হয়েছে।")

    # পিডিএফ হ্যান্ডলার
    elif update.message.document and update.message.document.file_name.lower().endswith('.pdf'):
        doc = await update.message.document.get_file()
        path = f"edit_{user_id}.pdf"
        await doc.download_to_drive(path)
        pdf_edit_files[user_id] = path
        btns = [[InlineKeyboardButton("🔄 Rotate 90°", callback_data='pdf_rotate')]]
        await update.message.reply_text("📄 PDF পাওয়া গেছে! কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন ক্লিক (Callback Query) ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # ভিডিও ইনফো
    if query.data == 'v_info':
        await query.message.reply_text("💡 শুধু ভিডিওর লিংকটি এখানে পেস্ট করলেই হবে।")

    # টেক্সট টু স্পিচ (ভয়েস জেনারেটর)
    elif query.data.startswith('tts_'):
        text = context.user_data.get('tts_text')
        # gTTS এ মেল/ফিমেল সরাসরি নেই, তবে আমরা স্পিড দিয়ে কিছুটা পরিবর্তন করি
        slow = True if query.data == 'tts_male' else False
        path = f"tts_{user_id}.mp3"
        gTTS(text=text, lang='bn', slow=slow).save(path)
        await context.bot.send_audio(chat_id=user_id, audio=open(path, 'rb'), caption="✅ ভয়েস তৈরি সম্পন্ন!")
        os.remove(path)
        context.user_data.clear()

    # ইমেজ টু পিডিএফ কনভার্ট
    elif query.data == 'convert_img_pdf':
        if user_id in user_images and user_images[user_id]:
            msg = await query.message.reply_text("⏳ পিডিএফ তৈরি হচ্ছে...")
            imgs = [Image.open(f).convert('RGB') for f in user_images[user_id]]
            pdf_path = f"gallery_{user_id}.pdf"
            imgs[0].save(pdf_path, save_all=True, append_images=imgs[1:])
            await context.bot.send_document(chat_id=user_id, document=open(pdf_path, 'rb'), caption="✅ PDF ফাইল রেডি!")
            for f in user_images[user_id]: os.remove(f)
            os.remove(pdf_path)
            del user_images[user_id]
            await msg.delete()

    # পিডিএফ রোটেট
    elif query.data == 'pdf_rotate':
        path = pdf_edit_files.get(user_id)
        if path:
            reader = PdfReader(path); writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
                writer.pages[-1].rotate(90)
            out = f"rot_{user_id}.pdf"
            with open(out, "wb") as f: writer.write(f)
            await context.bot.send_document(chat_id=user_id, document=open(out, 'rb'), caption="✅ রোটেট করা ফাইল।")
            os.remove(out); os.remove(path); del pdf_edit_files[user_id]

    # ভিডিও ডাউনলোড
    elif query.data in ['dl_v', 'dl_a']:
        url = context.user_data.get('url')
        mode = 'v' if query.data == 'dl_v' else 'a'
        await query.edit_message_text("⏳ প্রসেসিং শুরু হয়েছে... একটু অপেক্ষা করুন।")
        opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'max_filesize': 48*1024*1024}
        if mode == 'a': opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True); path = ydl.prepare_filename(info)
                if mode == 'a': path = path.rsplit('.', 1)[0] + ".mp3"
                await context.bot.send_document(chat_id=user_id, document=open(path, 'rb'), caption="✅ ফাইল ডাউনলোড সম্পন্ন!")
                os.remove(path)
        except: await query.message.reply_text("❌ ডাউনলোড ব্যর্থ! লিংক ভুল বা ফাইল বড়।")

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.PDF, handle_files))
    app.add_handler(CallbackQueryHandler(callback))
    print("🚀 All-in-One Professional Bot is LIVE!")
    app.run_polling()
