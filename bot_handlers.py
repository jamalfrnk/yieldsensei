from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from services.coingecko_service import get_token_price
from services.technical_analysis import get_technical_analysis
from services.openai_service import get_crypto_news
from utils.rate_limiter import rate_limit
from utils.cache import cache

HELP_TEXT = """
Welcome to Yield Sensei! Here are the available commands:

/price <token> - Get current price of a token
/technical <token> - Get technical analysis
/news - Get latest crypto news
/help - Show this help message

Example: /price BTC
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to Yield Sensei! 🚀\n\n"
        "I'm your AI-powered DeFi assistant. Use /help to see available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(HELP_TEXT)

@rate_limit
@cache
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token price."""
    if not context.args:
        await update.message.reply_text("Please provide a token symbol. Example: /price BTC")
        return

    token = context.args[0].lower()
    try:
        price_data = await get_token_price(token)
        await update.message.reply_text(
            f"💰 {token.upper()} Price:\n"
            f"USD: ${price_data['usd']:,.2f}\n"
            f"24h Change: {price_data['usd_24h_change']:.2f}%"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
@cache
async def technical_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get technical analysis."""
    if not context.args:
        await update.message.reply_text("Please provide a token symbol. Example: /technical BTC")
        return

    token = context.args[0].lower()
    try:
        analysis = await get_technical_analysis(token)
        await update.message.reply_text(
            f"📊 Technical Analysis for {token.upper()}:\n\n"
            f"RSI: {analysis['rsi']:.2f}\n"
            f"MACD: {analysis['macd_signal']}\n"
            f"Bollinger Bands: {analysis['bb_signal']}\n"
            f"Recommendation: {analysis['recommendation']}"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get latest crypto news."""
    try:
        news = await get_crypto_news()
        await update.message.reply_text(news)
    except Exception as e:
        await update.message.reply_text(str(e))