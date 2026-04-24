import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid
import requests

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes
)

# ------------------ LOGGING ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ ENV ------------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing in environment variables")

# ------------------ RAILWAY DUMMY SERVER ------------------
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

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot is online.\n\n"
        "Send a direct download link and I will fetch the file and return it."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to use:\n"
        "1. Send a direct file URL (http/https)\n"
        "2. Wait while I download it\n"
        "3. I will send the file back in Telegram\n\n"
        "Notes:\n"
        "- Must be direct download links\n"
        "- Some cloud links (Google Drive preview) may fail\n"
    )

# ------------------ DOWNLOAD LOGIC ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text

        if not text or not text.startswith("http"):
            await update.message.reply_text("Send a valid direct download link.")
            return

        logger.info(f"Downloading: {text}")
        await update.message.reply_text("Downloading...")

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}"

        with requests.get(text, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        await update.message.reply_text("Uploading...")

        await update.message.reply_document(document=open(file_path, "rb"))

        os.remove(file_path)

        logger.info("Done")

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Failed to download file.")

# ------------------ MAIN ------------------
def main():
    logger.info("Starting bot...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()