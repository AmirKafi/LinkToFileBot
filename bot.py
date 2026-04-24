from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import zipfile
import os
import uuid

TOKEN = os.getenv("BOT_TOKEN")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file = await doc.get_file()

    unique_id = str(uuid.uuid4())
    input_path = f"/tmp/{unique_id}_{doc.file_name}"
    zip_path = f"/tmp/{unique_id}.zip"

    await file.download_to_drive(input_path)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(input_path, arcname=doc.file_name)

    await update.message.reply_document(document=open(zip_path, 'rb'))

app = Application.builder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.Document.ALL, handle_files))

app.run_polling()