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

from playwright.sync_api import sync_playwright

# ------------------ LOGGING ------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN missing")

# ------------------ HELPERS ------------------
def is_url(text: str):
    return text.startswith("http://") or text.startswith("https://")


def download_requests(url, path):
    headers = {"User-Agent": "Mozilla/5.0"}

    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()

        ctype = r.headers.get("Content-Type", "")
        if "text/html" in ctype:
            raise Exception("Blocked or HTML response")

        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def download_playwright(url, path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        response = page.goto(url, wait_until="networkidle", timeout=60000)

        if not response:
            browser.close()
            raise Exception("No response from browser")

        content = response.body()

        with open(path, "wb") as f:
            f.write(content)

        browser.close()

# ------------------ COMMANDS ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Universal Downloader is online.\n\n"
        "Send any download link."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How it works:\n"
        "1. Send a URL\n"
        "2. Bot tries direct download\n"
        "3. If blocked → browser fallback\n\n"
        "Works best with direct file links and Gofile."
    )

# ------------------ HANDLER ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = update.message.text

        if not url or not is_url(url):
            await update.message.reply_text("Send a valid URL.")
            return

        await update.message.reply_text("Downloading...")

        file_id = str(uuid.uuid4())
        file_path = f"/tmp/{file_id}"

        # Step 1: try requests
        try:
            download_requests(url, file_path)
        except Exception as e:
            logger.warning(f"Requests failed: {e}")
            await update.message.reply_text("Trying browser mode...")

            # Step 2: fallback to browser
            download_playwright(url, file_path)

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