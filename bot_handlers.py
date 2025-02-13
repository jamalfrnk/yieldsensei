from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from services.coingecko_service import get_token_price
from services.technical_analysis import get_technical_analysis
from services.openai_service import get_crypto_news, process_nlp_query
from services.firebase_service import store_user_query
from utils.rate_limiter import rate_limit
from utils.cache import cache

HELP_TEXT = """
Welcome to Yield Sensei! 🎯 Here are the available commands:

/price <token> - Get current price and 24h change of a token
/technical <token> - Get detailed technical analysis with indicators
/news - Get latest AI-powered crypto market insights
/help - Show this help message

Example: /price btc
        /technical eth

You can also ask me any questions about crypto and DeFi! 💬
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to Yield Sensei! 🚀\n\n"
        "I'm your AI-powered DeFi assistant, ready to help you with:\n"
        "• Real-time crypto prices 💰\n"
        "• Technical analysis 📊\n"
        "• Market insights 📈\n"
        "• Any questions about crypto and DeFi! 💬\n\n"
        "Use /help to see all available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(HELP_TEXT)

@rate_limit
@cache
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token price."""
    if not context.args:
        await update.message.reply_text("Please provide a token symbol. Example: /price btc")
        return

    token = context.args[0].lower()
    try:
        price_data = await get_token_price(token)
        change = price_data['usd_24h_change']
        change_emoji = "🟢" if change >= 0 else "🔴"

        await update.message.reply_text(
            f"💰 {token.upper()} Price Analysis\n\n"
            f"Current Price: ${price_data['usd']:,.2f}\n"
            f"24h Change: {change_emoji} {abs(change):.2f}%\n\n"
            f"Use /technical {token} for more analysis"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
@cache
async def technical_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get technical analysis."""
    if not context.args:
        await update.message.reply_text("Please provide a token symbol. Example: /technical btc")
        return

    token = context.args[0].lower()
    try:
        analysis = await get_technical_analysis(token)

        # Determine RSI conditions
        rsi = analysis['rsi']
        rsi_status = "Oversold 📉" if rsi < 30 else "Overbought 📈" if rsi > 70 else "Neutral ⚖️"

        await update.message.reply_text(
            f"📊 Technical Analysis for {token.upper()}\n\n"
            f"RSI ({rsi:.1f}): {rsi_status}\n"
            f"MACD Signal: {analysis['macd_signal']} {'🟢' if analysis['macd_signal'] == 'Bullish' else '🔴'}\n"
            f"Bollinger Bands: {analysis['bb_signal']}\n\n"
            f"Overall: {analysis['recommendation']} {'🎯' if 'Strong' in analysis['recommendation'] else '⚖️'}\n\n"
            f"Remember: This is not financial advice. Always DYOR 📚"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get latest crypto news."""
    try:
        news = await get_crypto_news()
        await update.message.reply_text(
            "🗞️ Latest Crypto Market Insights:\n\n" + news
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Error: Unable to fetch crypto news at the moment. Please try again later."
        )

@rate_limit
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language messages."""
    message = update.message.text

    # Store the query in Firebase
    await store_user_query(
        user_id=update.effective_user.id,
        command="nlp",
        query=message
    )

    # Process the query using OpenAI
    response = await process_nlp_query(message)

    await update.message.reply_text(response)