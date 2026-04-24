import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import zipfile
import uuid

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ------------------ LOGGING ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ ENV ------------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in environment variables")

# ------------------ DUMMY SERVER (FOR RAILWAY) ------------------
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    logger.info(f"Dummy server running on port {port}")
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

# ------------------ BOT LOGIC ------------------
async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        doc = update.message.document
        if not doc:
            return

        logger.info(f"Received file: {doc.file_name}")

        file = await doc.get_file()

        unique_id = str(uuid.uuid4())
        input_path = f"/tmp/{unique_id}_{doc.file_name}"
        zip_path = f"/tmp/{unique_id}.zip"

        await file.download_to_drive(input_path)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(input_path, arcname=doc.file_name)

        await update.message.reply_document(document=open(zip_path, 'rb'))

        # cleanup
        os.remove(input_path)
        os.remove(zip_path)

        logger.info("File processed and sent successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Error processing file.")

# ------------------ START BOT ------------------
def main():
    logger.info("Starting bot...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_files))

    app.run_polling()

if __name__ == "__main__":
    main()