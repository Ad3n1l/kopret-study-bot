# Limlo Study Bot - Railway Deployment Guide

A Telegram study bot powered by Google Gemini AI for Ahmadu Bello University students.

## Files Structure

```
limlo-study-bot/
├── bot.py              # Main bot code
├── requirements.txt    # Python dependencies
├── Procfile           # Railway process configuration
├── runtime.txt        # Python version
└── README.md          # This file
```

## Deployment Steps on Railway

### 1. Get Your API Keys

**Telegram Bot Token:**
1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the prompts to name your bot (e.g., "Limlo Study Bot")
4. Copy the token BotFather gives you

**Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key
4. Copy the key

### 2. Deploy to Railway

1. **Create Railway Account:**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account if needed
   - Select your repository with the bot code

3. **Add Environment Variables:**
   - In your Railway project dashboard, go to "Variables"
   - Add the following variables:
     - `TELEGRAM_BOT_TOKEN` = your_telegram_bot_token
     - `GEMINI_API_KEY` = your_gemini_api_key

4. **Deploy:**
   - Railway will automatically detect your Procfile and deploy
   - Wait for deployment to complete (usually 1-2 minutes)

### 3. Verify Deployment

1. Check the deployment logs in Railway dashboard
2. Look for the message: "Starting Limlo Study Bot..."
3. Open Telegram and search for your bot
4. Send `/start` to test

## Bot Commands

- `/start` - Welcome message and introduction
- `/help` - How to use the bot
- `/clear` - Clear conversation history

## Features

- ✅ AI-powered responses using Google Gemini
- ✅ Conversation memory (remembers context)
- ✅ Study-focused guidance
- ✅ Step-by-step explanations
- ✅ ABU-branded experience

## Troubleshooting

**Bot not responding:**
- Check Railway logs for errors
- Verify environment variables are set correctly
- Ensure your API keys are valid

**"Missing required environment variables" error:**
- Make sure both `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` are added in Railway Variables

**Gemini API errors:**
- Check your Gemini API quota
- Verify the API key is correct

## Cost

- **Railway:** Free tier available (500 hours/month)
- **Gemini API:** Free tier includes 60 requests per minute
- **Telegram Bot:** Completely free

## Support

For issues or suggestions, please create an issue in the repository.

## License

MIT License - feel free to modify and use for your purposes!

---

**Go ABU Great Ife!** 🦅💚🤍
