import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import io

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
    raise ValueError("Missing required environment variables: GEMINI_API_KEY and TELEGRAM_BOT_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

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
• 📸 Send images of diagrams, equations, or notes for analysis!

Commands:
/start - Show this welcome message
/clear - Clear conversation history
/help - Get help on how to use me

Just send me your question or image and I'll do my best to help! 📚

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

5️⃣ 📸 Send images:
   • Mathematical equations
   • Diagrams and charts
   • Handwritten notes
   • Textbook pages
   • Lab results
   
   Add a caption with your question about the image!

💡 Tips:
• Be specific with your questions
• I remember our conversation, so you can ask follow-up questions
• Use /clear to start a new topic
• For images, add a caption describing what you need help with

Happy studying, ABU student! 🦅📚✨

Go Great Ife! 💚🤍
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages and generate responses using Gemini"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Initialize conversation history if needed
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Send "thinking" message
    thinking_messages = [
        "🤔 Thinking...",
        "💭 Let me think about that...",
        "🧠 Processing your question...",
        "📚 Looking into this...",
        "🔍 Analyzing..."
    ]
    
    import random
    thinking_msg = await update.message.reply_text(random.choice(thinking_messages))
    
    try:
        # Create a study-focused prompt
        system_prompt = """You are Limlo Study Bot, a helpful AI study assistant created specifically for Ahmadu Bello University (ABU) students. Your role is to:
- Explain concepts clearly and thoroughly but concisely
- Break down complex topics into understandable parts
- Provide examples and analogies relevant to ABU students when possible
- Guide students to understand, not just give direct answers
- Encourage critical thinking and academic excellence
- Be patient, supportive, and encouraging
- Celebrate ABU's academic tradition of excellence
- Keep responses under 3000 characters when possible for better readability

When helping with assignments, guide the student through the problem rather than just providing the answer. Support ABU students in their journey to academic success!"""
        
        # Build conversation context with recent history (last 5 exchanges)
        conversation_context = ""
        recent_history = user_conversations[user_id][-10:]  # Last 10 messages (5 exchanges)
        
        if recent_history:
            conversation_context = "\n\nRecent conversation:\n"
            for msg in recent_history:
                conversation_context += f"{msg}\n"
        
        # Create full prompt
        full_prompt = f"{system_prompt}{conversation_context}\n\nStudent question: {user_message}"
        
        # Generate response
        response = model.generate_content(full_prompt)
        bot_response = response.text
        
        # Delete the "thinking" message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=thinking_msg.message_id
        )
        
        # Store conversation
        user_conversations[user_id].append(f"Student: {user_message}")
        user_conversations[user_id].append(f"Limlo: {bot_response}")
        
        # Keep only last 20 messages to manage memory
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]
        
        # Send response (split if too long)
        # Telegram max message length is 4096 characters
        max_length = 4000  # Leave some buffer
        
        if len(bot_response) <= max_length:
            await update.message.reply_text(bot_response)
        else:
            # Split message into chunks
            chunks = []
            current_chunk = ""
            
            # Split by paragraphs first
            paragraphs = bot_response.split('\n\n')
            
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) + 2 <= max_length:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(f"(continued...)\n\n{chunk}")
        
        logger.info(f"Responded to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        
        # Delete the "thinking" message if it exists
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=thinking_msg.message_id
            )
        except:
            pass
        
        error_message = """
😔 Sorry, I encountered an error processing your question. 

Please try:
• Rephrasing your question
• Using /clear to start fresh
• Asking a different question

If the problem persists, please contact support.
        """
        await update.message.reply_text(error_message)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos and analyze them using Gemini Vision"""
    user_id = update.effective_user.id
    
    # Initialize conversation history if needed
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Send "analyzing" message
    analyzing_messages = [
        "📸 Analyzing your image...",
        "🔍 Examining the image...",
        "👀 Looking at your image...",
        "🧠 Processing the image...",
        "📊 Analyzing the diagram..."
    ]
    
    import random
    thinking_msg = await update.message.reply_text(random.choice(analyzing_messages))
    
    try:
        # Get the largest photo (highest resolution)
        photo = update.message.photo[-1]
        
        # Download the photo
        photo_file = await context.bot.get_file(photo.file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Get caption if provided
        caption = update.message.caption if update.message.caption else "What can you tell me about this image? Please analyze it in detail."
        
        # Create a study-focused prompt for image analysis
        system_prompt = """You are Limlo Study Bot, analyzing an image for an Ahmadu Bello University student. When analyzing images:
- Identify what the image contains (diagram, equation, notes, chart, etc.)
- Explain key concepts shown in the image
- If it's a problem, guide the student through solving it
- If it's notes or text, help clarify difficult concepts
- Point out important details the student should notice
- Be thorough but concise (under 3000 characters when possible)
- Always maintain an encouraging, educational tone

Help the student understand and learn from what they've shared!"""
        
        prompt = f"{system_prompt}\n\nStudent's question about the image: {caption}"
        
        # Generate response using vision model
        response = model.generate_content([prompt, image])
        bot_response = response.text
        
        # Delete the "analyzing" message
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=thinking_msg.message_id
        )
        
        # Store conversation
        user_conversations[user_id].append(f"Student: [Sent image] {caption}")
        user_conversations[user_id].append(f"Limlo: {bot_response}")
        
        # Keep only last 20 messages to manage memory
        if len(user_conversations[user_id]) > 20:
            user_conversations[user_id] = user_conversations[user_id][-20:]
        
        # Send response (split if too long)
        max_length = 4000
        
        if len(bot_response) <= max_length:
            await update.message.reply_text(bot_response)
        else:
            # Split message into chunks
            chunks = []
            current_chunk = ""
            
            paragraphs = bot_response.split('\n\n')
            
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) + 2 <= max_length:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = paragraph + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Send each chunk
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(f"(continued...)\n\n{chunk}")
        
        logger.info(f"Analyzed image for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        
        # Delete the "analyzing" message if it exists
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=thinking_msg.message_id
            )
        except:
            pass
        
        error_message = """
😔 Sorry, I encountered an error analyzing your image. 

Please try:
• Sending a clearer image
• Adding a caption describing what you need help with
• Making sure the image is not too large

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
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting Limlo Study Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()