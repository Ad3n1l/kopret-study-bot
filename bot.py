import os
import logging
import io
from datetime import datetime, timedelta
from collections import defaultdict
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configure API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN:
    raise ValueError(
        "Missing required environment variables: GEMINI_API_KEY and TELEGRAM_BOT_TOKEN"
    )

genai.configure(api_key=GEMINI_API_KEY)

# Initialize Gemini model
# Use gemini-1.5-flash for stable vision support
# Alternatives: gemini-1.5-pro, gemini-2.0-flash-exp
model = genai.GenerativeModel('gemini-1.5-flash')

# Store conversation history per user
user_conversations = {}

# Rate limiting
user_request_times = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 10


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued"""
    welcome_message = """
🎓 Welcome to Limlo Study Bot!

Your personal AI study companion for Ahmadu Bello University students! 🦅

I can now see! 👀 
• Send me a photo of your notes, assignments, or textbook pages
• Add a caption to ask a specific question about the image
• Or just chat with me normally for any academic help

Commands:
/start - Show this welcome message
/clear - Clear conversation history
/help - Get help on how to use me

Just send me your question (with or without a photo) and I'll help you learn! 📚
    """
    await update.message.reply_text(welcome_message)
    
    user_id = update.effective_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    logger.info(f"User {user_id} started the bot")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for the user"""
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")
    logger.info(f"User {user_id} cleared conversation history")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide help information"""
    help_text = """
📖 How to use Limlo Study Bot:

1️⃣ Image Analysis (NEW! 📸):
   • Snap a photo of a math problem, diagram, or notes
   • Add a caption like "Solve this" or "Explain this diagram"
   • I'll analyze the image and help you understand it

2️⃣ Text Questions:
   • "What is photosynthesis?"
   • "Explain Newton's laws of motion"
   • "Help me understand calculus derivatives"
   
💡 Tips:
• Ensure photos are clear and well-lit for best results
• I remember our conversation context
• Use /clear to start a new topic
• Ask follow-up questions naturally

Commands:
/start - Welcome message
/clear - Clear conversation history
/help - Show this help message

Happy studying, ABU student! 🦅
    """
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (text or photo) and generate responses"""
    user_id = update.effective_user.id
    
    # Rate limiting check
    now = datetime.now()
    user_request_times[user_id] = [
        t for t in user_request_times[user_id] 
        if now - t < timedelta(minutes=1)
    ]
    
    if len(user_request_times[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        await update.message.reply_text(
            "⏳ Slow down! Please wait a moment before sending more requests."
        )
        return
    
    user_request_times[user_id].append(now)
    
    # Get user message (caption if photo, text otherwise)
    user_message = update.message.text or update.message.caption or "Analyze this image"
    
    # Initialize conversation history if needed
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # Send "thinking" message
    thinking_msg = await update.message.reply_text("🤔 Analyzing...")

    try:
        # System prompt
        system_prompt = """You are Limlo Study Bot, a helpful AI study assistant created specifically for Ahmadu Bello University (ABU) students. Your role is to:

- Explain concepts clearly and thoroughly but concisely
- If analyzing an image, describe what you see and solve any problems present
- Break down complex topics into understandable parts
- Guide students to understand, not just give direct answers
- Use examples relevant to Nigerian students when possible
- Keep responses under 3000 characters when possible for readability

When helping with assignments, guide the student through the problem-solving process rather than just providing answers. Encourage critical thinking."""

        # Prepare input for Gemini
        gemini_input = []
        
        # Build context string with conversation history
        recent_history = "\n".join(user_conversations[user_id][-6:])
        context_str = f"{system_prompt}\n\n"
        
        if recent_history:
            context_str += f"Recent History:\n{recent_history}\n\n"
        
        context_str += f"Student Question: {user_message}"
        gemini_input.append(context_str)

        # Handle photo if present
        if update.message.photo:
            # Get the highest quality photo
            photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
            
            # Download to memory
            image_stream = io.BytesIO()
            await photo_file.download_to_memory(out=image_stream)
            image_stream.seek(0)
            
            # Convert to PIL Image
            image = Image.open(image_stream)
            gemini_input.append(image)
            logger.info(f"User {user_id} sent an image with caption: {user_message}")

        # Generate response from Gemini
        response = model.generate_content(gemini_input)
        bot_response = response.text

        # Delete thinking message
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=thinking_msg.message_id
            )
        except:
            pass

        # Update conversation history
        if update.message.photo:
            user_conversations[user_id].append(f"Student: {user_message} [Image Sent]")
        else:
            user_conversations[user_id].append(f"Student: {user_message}")
        
        user_conversations[user_id].append(f"Limlo: {bot_response}")
        
        # Keep only last 20 messages to manage memory
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]

        # Send response (handle long messages)
        max_length = 4000
        if len(bot_response) <= max_length:
            await update.message.reply_text(bot_response)
        else:
            # Split into chunks
            for i in range(0, len(bot_response), max_length):
                chunk = bot_response[i:i+max_length]
                await update.message.reply_text(chunk)
                
        logger.info(f"Successfully responded to user {user_id}")

    except genai.types.generation_types.BlockedPromptException:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=thinking_msg.message_id
            )
        except:
            pass
        await update.message.reply_text(
            "⚠️ That content was flagged by safety filters. Please rephrase your question or try a different image."
        )
        logger.warning(f"Blocked prompt for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error for user {user_id}: {e}", exc_info=True)
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=thinking_msg.message_id
            )
        except:
            pass
        await update.message.reply_text(
            "😔 I had trouble processing that. Please try again or use /help for guidance."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)


def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    
    # Register message handler (FIXED: proper filter syntax)
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO) & ~filters.COMMAND, 
        handle_message
    ))

    # Register error handler
    application.add_error_handler(error_handler)

    logger.info("🚀 Starting Limlo Study Bot...")
    logger.info("Bot is ready to help ABU students! 🦅")
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

