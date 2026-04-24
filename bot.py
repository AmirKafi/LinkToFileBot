import os
import logging
import uuid
import requests
import re

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

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# ------------------ HELPERS ------------------
def is_url(text: str):
    return bool(re.match(r"https?://", text))


def download_file(url: str, path: str):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }

    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()

        # If response is HTML, it's probably blocked
        content_type = r.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise Exception("Blocked or not a direct file")

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Universal Downloader Bot is online.\n\n"
        "Send any direct download link."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Supported:\n"
        "- Direct file links\n"
        "- Most CDN links\n\n"
        "May NOT work:\n"
        "- Google Drive preview\n"
        "- Mega links\n"
        "- Strong anti-bot sites\n"
    )

# ------------------ MAIN HANDLER ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text

        if not text or not is_url(text):
            await update.message.reply_text("Send a valid URL.")
            return

        await update.message.reply_text("Downloading...")

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}"

        try:
            download_file(text, file_path)
        except Exception as e:
            logger.warning(f"Direct download failed: {e}")
            await update.message.reply_text("Trying alternative method...")

            # fallback: simple retry with stronger headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Referer": text
            }

            with requests.get(text, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

        await update.message.reply_text("Uploading...")

        with open(file_path, "rb") as f:
            await update.message.reply_document(document=f)

        os.remove(file_path)

        await update.message.reply_text("Done.")

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("Failed to download this link.")

# ------------------ MAIN ------------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()