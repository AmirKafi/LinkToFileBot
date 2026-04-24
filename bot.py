import os
import logging
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ------------------ ENV ------------------
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot is online.\n\n"
        "Send a direct download link and I will fetch the file and return it."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Usage:\n"
        "1. Send a direct http/https download link\n"
        "2. Bot downloads the file\n"
        "3. Bot sends it back to you\n\n"
        "Notes:\n"
        "- Must be direct file links\n"
        "- Some cloud links may not work"
    )

# ------------------ DOWNLOAD HANDLER ------------------
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

        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f)

        os.remove(file_path)

        logger.info("Done")

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("Failed to download file.")

# ------------------ MAIN ------------------
def main():
    logger.info("Starting bot...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()