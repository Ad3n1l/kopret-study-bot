import os
import logging
import random
import asyncio
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- Configuration ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "Missing GEMINI_API_KEY or TELEGRAM_BOT_TOKEN environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Use gemini-1.5-flash for speed and cost-efficiency
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction=(
        "You are Limlo Study Bot, a helpful AI assistant for Ahmadu Bello University (ABU) students. "
        "Explain concepts clearly and thoroughly. Use analogies related to ABU or Nigeria when helpful. "
        "Guide students to answers rather than just giving them. Be encouraging and professional. "
        "Use Markdown for formatting (bold, bullet points, and LaTeX-style math where applicable)."
    )
)

# Store active chat sessions
# Note: In production, consider a database to persist these across restarts.
chat_sessions = {}

# --- Handlers ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"🎓 *Welcome to Limlo Study Bot, {user_name}!*\n\n"
        "Your AI study companion for ABU Zaria. 🦅\n\n"
        "• Ask me complex questions\n"
        "• Get help with study schedules\n"
        "• Simplify difficult lecture notes\n\n"
        "*Commands:*\n"
        "/clear - Start a new topic\n"
        "/help - See how to use me\n\n"
        "Ready to learn? Send me a message! 📚\n\n"
        "_Naturally Ahead..._ 💚🤍"
    )
    await update.message.reply_text(welcome_text, parse_mode=constants.ParseMode.MARKDOWN)


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in chat_sessions:
        del chat_sessions[user_id]
    await update.message.reply_text("✅ *Memory cleared!* What should we study next?", parse_mode=constants.ParseMode.MARKDOWN)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text

    # Show "typing..." status
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)

    # Initialize session if not exists
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    try:
        # Generate response
        response = await asyncio.to_thread(chat_sessions[user_id].send_message, user_input)

        # Telegram has a 4096 character limit
        full_text = response.text
        if len(full_text) > 4000:
            for i in range(0, len(full_text), 4000):
                await update.message.reply_text(full_text[i:i+4000])
        else:
            # We use try/except for Markdown because LLMs sometimes produce invalid Markdown syntax
            try:
                await update.message.reply_text(full_text, parse_mode=constants.ParseMode.MARKDOWN)
            except:
                await update.message.reply_text(full_text)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("⚠️ I'm having trouble connecting right now. Please try again in a moment!")

# --- Main ---


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    print("Limlo Bot is running...")
    application.run_polling()


if __name__ == '__main__':
    main()
