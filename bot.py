import os
import logging
import io  # Added for image processing
from PIL import Image  # Added for image processing
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

# Note: Ensure you are using a model that supports Vision (e.g., gemini-1.5-flash or gemini-1.5-pro)
# 'gemini-2.5-flash' might be a typo or a preview name. 
# Standardizing to 'gemini-1.5-flash' for guaranteed stability, but feel free to switch back.
model = genai.GenerativeModel('gemini-2.5-flash') 

# Store conversation history per user
user_conversations = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued"""
    welcome_message = """
🎓 Welcome to Limlo Study Bot!

Your personal AI study companion for Ahmadu Bello University students! 🦅

I can now see! 👀 
• Send me a photo of your notes, assignments, or textbook.
• Add a caption to ask a specific question.
• Or just chat with me normally.

Commands:
/start - Show this welcome message
/clear - Clear conversation history
/help - Get help on how to use me

Just send me your question (or photo) and I'll do my best to help! 📚
    """
    await update.message.reply_text(welcome_message)
    
    user_id = update.effective_user.id
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    logger.info(f"User {user_id} started the bot")


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")
    logger.info(f"User {user_id} cleared conversation history")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 How to use Limlo Study Bot:

1️⃣ Image Analysis (NEW! 📸):
   • Snap a photo of a math problem or diagram.
   • Add a caption like "Solve this" or "Explain this diagram".

2️⃣ Text Questions:
   • "What is photosynthesis?"
   • "Explain Newton's laws of motion"
   
💡 Tips:
• Ensure photos are clear and well-lit.
• I remember our conversation context.

Happy studying, ABU student! 🦅
    """
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (Text OR Photo) and generate responses"""
    user_id = update.effective_user.id
    
    # Get text caption if photo, or message text if just text
    user_message = update.message.text or update.message.caption or "Analyze this image"
    
    # Initialize conversation history
    if user_id not in user_conversations:
        user_conversations[user_id] = []

    # Send "thinking" message
    thinking_msg = await update.message.reply_text("🤔 Looking into this...")

    try:
        # --- PREPARE SYSTEM PROMPT ---
        system_prompt = """You are Limlo Study Bot, a helpful AI study assistant created specifically for Ahmadu Bello University (ABU) students. Your role is to:
- Explain concepts clearly and thoroughly but concisely
- If analyzing an image, describe what you see and solve any problems present
- Break down complex topics into understandable parts
- Guide students to understand, not just give direct answers
- Keep responses under 3000 characters when possible

When helping with assignments, guide the student through the problem."""

        # --- HANDLE IMAGE VS TEXT ---
        gemini_input = []
        
        # 1. Add System Prompt and Context to input
        # Note: For vision requests, we often pass history as text blocks before the image
        context_str = f"{system_prompt}\n\nRecent History:\n" + "\n".join(user_conversations[user_id][-6:]) + f"\n\nStudent Question: {user_message}"
        gemini_input.append(context_str)

        # 2. Check for Photo
        if update.message.photo:
            # Get the largest available photo file
            photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
            
            # Download to memory (byte stream)
            image_stream = io.BytesIO()
            await photo_file.download_to_memory(out=image_stream)
            image_stream.seek(0)
            
            # Convert to PIL Image
            image = Image.open(image_stream)
            gemini_input.append(image)  # Add image to Gemini input list
            logger.info(f"User {user_id} sent an image")

        # --- GENERATE CONTENT ---
        # Gemini accepts a list [text, image] for multimodal prompts
        response = model.generate_content(gemini_input)
        bot_response = response.text

        # Cleanup thinking message
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=thinking_msg.message_id)

        # Update History (Store text representation only to save memory)
        user_conversations[user_id].append(f"Student: {user_message} [Image Sent]" if update.message.photo else f"Student: {user_message}")
        user_conversations[user_id].append(f"Limlo: {bot_response}")
        
        # Keep history short
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]

        # --- SEND RESPONSE (Chunking) ---
        max_length = 4000
        if len(bot_response) <= max_length:
            await update.message.reply_text(bot_response)
        else:
            # Simple chunking loop
            for x in range(0, len(bot_response), max_length):
                await update.message.reply_text(bot_response[x:x+max_length])

    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=thinking_msg.message_id)
        except:
            pass
        await update.message.reply_text("😔 I had trouble seeing or processing that. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update caused error {context.error}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    
    # UPDATE: Filter now accepts Text OR Photo
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO & ~filters.COMMAND, handle_message))

    application.add_error_handler(error_handler)

    logger.info("Starting Limlo Study Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

