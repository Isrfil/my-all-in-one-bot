import os, qrcode, asyncio, httpx, fitz, time
from pypdf import PdfReader, PdfWriter
from yt_dlp import YoutubeDL
from PIL import Image, ImageOps, ImageFilter
from gtts import gTTS
import pyshorteners
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# --- Flask Server (Keep Alive) ---
app_web = Flask('')
@app_web.route('/')
def home(): return "All-in-One Office Bot is Online!"
def run(): app_web.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- কনফিগারেশন ---
TOKEN = "8681613014:AAGhaxmwY5Xv_F1FDDyccUwIqT05WXUAQ3M"
ADMIN_ID = 6365947320

user_images = {}
pdf_edit_files = {}

# --- মেইন কিবোর্ড ---
def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📱 ভিডিও ডাউনলোড"), KeyboardButton("📂 Office টুলস")],
        [KeyboardButton("📄 PDF টুলস"), KeyboardButton("🖼 ইমেজ এডিটর")],
        [KeyboardButton("🔍 QR & Link"), KeyboardButton("🗣 ভয়েস মেসেজ")]
    ], resize_keyboard=True, is_persistent=True)

# --- সাব-মেনুসমূহ ---
def office_tools_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Word (Docx) তৈরি", callback_data='off_word')],
        [InlineKeyboardButton("📊 Excel (Xlsx) তৈরি", callback_data='off_excel')],
        [InlineKeyboardButton("📽 PPT (Slides) তৈরি", callback_data='off_ppt')]
    ])

# --- স্টার্ট কমান্ড ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"🌟 **Professional Multi-Tasker Bot**\nস্বাগতম {update.effective_user.first_name}!\nসব ধরণের ফাইল কনভার্ট ও তৈরির জন্য নিচের মেনু ব্যবহার করুন।",
        reply_markup=main_keyboard(), parse_mode="Markdown"
    )

# --- টেক্সট মেসেজ হ্যান্ডলার ---
async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    state = context.user_data.get('state')

    if text == "📂 Office টুলস":
        await update.message.reply_text("📑 আপনি কি ফাইল তৈরি করতে চান?", reply_markup=office_tools_menu())
    
    elif text == "📱 ভিডিও ডাউনলোড":
        await update.message.reply_text("🎬 ভিডিওর লিংক এখানে পেস্ট করুন।")
    
    elif text == "📄 PDF টুলস":
        await update.message.reply_text("📂 একটি PDF ফাইল পাঠান অথবা ইমেজ থেকে PDF করতে '🖼 ইমেজ এডিটর' এ যান।")

    elif text == "🖼 ইমেজ এডিটর":
        user_images[user_id] = []
        await update.message.reply_text("📸 ছবি পাঠান (এডিট করতে) বা একাধিক ছবি পাঠান (PDF বানাতে)।")

    # --- Office ফাইল তৈরির লজিক ---
    elif state == 'WAIT_WORD':
        doc = Document()
        doc.add_paragraph(text)
        path = f"doc_{user_id}.docx"
        doc.save(path)
        await update.message.reply_document(document=open(path, 'rb'), caption="✅ আপনার Word ফাইল তৈরি সম্পন্ন!")
        os.remove(path); context.user_data.clear()

    elif state == 'WAIT_EXCEL':
        wb = Workbook(); ws = wb.active
        # কমা দিয়ে আলাদা করা ডাটা লিস্ট হিসেবে নেবে
        for row_data in text.split('\n'):
            ws.append(row_data.split(','))
        path = f"sheet_{user_id}.xlsx"
        wb.save(path)
        await update.message.reply_document(document=open(path, 'rb'), caption="✅ আপনার Excel ফাইল তৈরি সম্পন্ন!")
        os.remove(path); context.user_data.clear()

    elif state == 'WAIT_PPT':
        prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Presentation by Bot"
        slide.placeholders[1].text = text
        path = f"pres_{user_id}.pptx"
        prs.save(path)
        await update.message.reply_document(document=open(path, 'rb'), caption="✅ আপনার PowerPoint ফাইল তৈরি সম্পন্ন!")
        os.remove(path); context.user_data.clear()

    # কিউআর ও শর্টেনার
    elif text == "🔍 QR & Link":
        btns = [[InlineKeyboardButton("🔍 QR Code", callback_data='m_qr'), InlineKeyboardButton("🔗 Link Short", callback_data='m_short')]]
        await update.message.reply_text("কি করতে চান?", reply_markup=InlineKeyboardMarkup(btns))

    elif text.startswith("http"):
        context.user_data['url'] = text
        btns = [[InlineKeyboardButton("🎬 Video", callback_data='dl_v'), InlineKeyboardButton("🎵 MP3", callback_data='dl_a')]]
        await update.message.reply_text("🔗 লিংক পাওয়া গেছে!", reply_markup=InlineKeyboardMarkup(btns))

# --- বাটন ক্লিক একশনস ---
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'off_word':
        context.user_data['state'] = 'WAIT_WORD'
        await query.message.reply_text("📝 আপনার ডকুমেন্টের লেখাটুকু পাঠান (আমি সেটি .docx ফাইলে সেভ করে দেব):")
    
    elif data == 'off_excel':
        context.user_data['state'] = 'WAIT_EXCEL'
        await query.message.reply_text("📊 ডাটা পাঠান (যেমন: Name, Age, City)। প্রতি লাইনে নতুন রো দিন:")
    
    elif data == 'off_ppt':
        context.user_data['state'] = 'WAIT_PPT'
        await query.message.reply_text("📽 স্লাইডের জন্য টেক্সট পাঠান:")

    # আগের অন্যান্য বাটন লজিক (ইমেজ, ভিডিও ইত্যাদি)
    elif data == 'm_qr': context.user_data['state'] = 'QR'; await query.message.reply_text("লিংক পাঠান:")
    # ... (বাকি আগের কোড অনুযায়ী কাজ করবে)

# --- ফাইল হ্যান্ডলার (Image, PDF, Document) ---
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (ইমেজ এবং পিডিএফ প্রসেসিং লজিক আগের কোড থেকে থাকবে)
    pass

if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).read_timeout(100).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_files))
    app.add_handler(CallbackQueryHandler(callback))
    app.run_polling()
