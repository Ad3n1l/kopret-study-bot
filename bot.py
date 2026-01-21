import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "Missing required environment variables: GEMINI_API_KEY and TELEGRAM_BOT_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Store conversation history per user
user_conversations = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued"""
    welcome_message = """
🎓 Welcome to Limlo Study Bot!

Your personal AI study companion for Ahmadu Bello University students! 🦅

I'm here to help you excel in your studies. You can:
• Ask me any question about any subject
• Request explanations of complex topics
• Get help with assignments (I'll guide you, not just give answers!)
• Practice with quizzes and problems
• Study for exams

Commands:
/start - Show this welcome message
/clear - Clear conversation history
/help - Get help on how to use me

Just send me your question and I'll do my best to help! 📚

Go ABU Great Ife! 💚🤍
    """
    await update.message.reply_text(welcome_message)

    # Initialize conversation for new users
    user_id = update.effective_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    logger.info(f"User {user_id} started the bot")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear the conversation history for the user"""
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")
    logger.info(f"User {user_id} cleared conversation history")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide help information"""
    help_text = """
📖 How to use Limlo Study Bot:

1️⃣ Ask questions naturally:
   "What is photosynthesis?"
   "Explain Newton's laws of motion"
   
2️⃣ Request step-by-step solutions:
   "How do I solve quadratic equations?"
   "Walk me through mitosis"
   
3️⃣ Get study tips:
   "How can I memorize the periodic table?"
   
4️⃣ Practice problems:
   "Give me a practice problem on algebra"

💡 Tips:
• Be specific with your questions
• I remember our conversation, so you can ask follow-up questions
• Use /clear to start a new topic

Happy studying, ABU student! 🦅📚✨

Go Great Ife! 💚🤍
    """
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and generate responses using Gemini"""
    user_id = update.effective_user.id
    user_message = update.message.text

    # Initialize conversation history if needed
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Create a study-focused prompt
        system_prompt = """You are Limlo Study Bot, a helpful AI study assistant created specifically for Ahmadu Bello University (ABU) students. Your role is to:
- Explain concepts clearly and thoroughly
- Break down complex topics into understandable parts
- Provide examples and analogies relevant to ABU students when possible
- Guide students to understand, not just give direct answers
- Encourage critical thinking and academic excellence
- Be patient, supportive, and encouraging
- Celebrate ABU's academic tradition of excellence

When helping with assignments, guide the student through the problem rather than just providing the answer. Support ABU students in their journey to academic success!"""

        # Build conversation context with recent history (last 5 exchanges)
        conversation_context = ""
        # Last 10 messages (5 exchanges)
        recent_history = user_conversations[user_id][-10:]

        if recent_history:
            conversation_context = "\n\nRecent conversation:\n"
            for msg in recent_history:
                conversation_context += f"{msg}\n"

        # Create full prompt
        full_prompt = f"{system_prompt}{conversation_context}\n\nStudent question: {user_message}"

        # Generate response
        response = model.generate_content(full_prompt)
        bot_response = response.text

        # Store conversation
        user_conversations[user_id].append(f"Student: {user_message}")
        user_conversations[user_id].append(f"Limlo: {bot_response}")

        # Keep only last 20 messages to manage memory
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]

        # Send response
        await update.message.reply_text(bot_response)
        logger.info(f"Responded to user {user_id}")

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        error_message = """
😔 Sorry, I encountered an error processing your question. 

Please try:
• Rephrasing your question
• Using /clear to start fresh
• Asking a different question

If the problem persists, please contact support.
        """
        await update.message.reply_text(error_message)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting Limlo Study Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
