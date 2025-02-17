from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from services.coingecko_service import get_token_price, get_token_market_data
from services.technical_analysis import get_technical_analysis
from services.openai_service import get_crypto_news, process_nlp_query
from services.firebase_service import store_user_query
from utils.rate_limiter import rate_limit
from utils.cache import cache

BOT_USERNAME = "yieldsensei_bot"
HELP_TEXT = """
Welcome to Yield Sensei! 🎯 Here are the available commands:

📊 Market Data Commands (via CoinGecko):
@yieldsensei_bot /price <token> - Get current price and 24h change
@yieldsensei_bot /market <token> - Get market cap, volume, and 24h high/low
@yieldsensei_bot /technical <token> - Get technical analysis with indicators

🤖 AI-Powered Features (via OpenAI):
@yieldsensei_bot /news - Get latest crypto market insights
@yieldsensei_bot <question> - Ask anything about crypto/DeFi!

ℹ️ General Commands:
@yieldsensei_bot /help - Show this help message
@yieldsensei_bot /start - Get started with Yield Sensei

Examples:
Market Data: @yieldsensei_bot /price btc
            @yieldsensei_bot /market eth
            @yieldsensei_bot /technical sol

AI Chat: @yieldsensei_bot what is yield farming?
        @yieldsensei_bot explain how DEX works
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to Yield Sensei! 🚀\n\n"
        "I'm your AI-powered DeFi assistant, ready to help you with:\n"
        "• Real-time crypto prices 💰\n"
        "• Market data and analysis 📊\n"
        "• Technical analysis 📈\n"
        "• AI-powered insights 🤖\n"
        "• Any questions about crypto and DeFi! 💬\n\n"
        f"Just start your message with @{BOT_USERNAME}\n"
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
        await update.message.reply_text(f"Please provide a token symbol. Example: @{BOT_USERNAME} /price btc")
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
            f"Use @{BOT_USERNAME} /market {token} for more details"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
@cache
async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed market data."""
    if not context.args:
        await update.message.reply_text(f"Please provide a token symbol. Example: @{BOT_USERNAME} /market btc")
        return

    token = context.args[0].lower()
    try:
        market_data = await get_token_market_data(token)

        # Format large numbers
        market_cap = f"${market_data['market_cap']:,.0f}"
        volume = f"${market_data['total_volume']:,.0f}"

        await update.message.reply_text(
            f"📊 {token.upper()} Market Data\n\n"
            f"Market Cap: {market_cap}\n"
            f"Rank: #{market_data['market_cap_rank']}\n"
            f"24h Volume: {volume}\n"
            f"24h High: ${market_data['high_24h']:,.2f}\n"
            f"24h Low: ${market_data['low_24h']:,.2f}\n"
            f"24h Change: {market_data['price_change_percentage_24h']:.2f}%\n\n"
            f"Use @{BOT_USERNAME} /technical {token} for analysis"
        )
    except Exception as e:
        await update.message.reply_text(str(e))

@rate_limit
@cache
async def technical_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get technical analysis."""
    if not context.args:
        await update.message.reply_text(f"Please provide a token symbol. Example: @{BOT_USERNAME} /technical btc")
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
            "📰 Latest Crypto Market Insights:\n\n" + 
            news + "\n\n" +
            "💡 Want to learn more?\n" +
            f"- Ask me anything with @{BOT_USERNAME} <your question>\n" +
            f"- Check market data with @{BOT_USERNAME} /market <token>\n" +
            f"- Get technical analysis with @{BOT_USERNAME} /technical <token>"
        )
    except Exception as e:
        await update.message.reply_text(
            "❌ Error: Unable to fetch crypto news at the moment. Please try again later."
        )

@rate_limit
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language messages."""
    message = update.message.text

    # Check if message starts with @yieldsensei_bot
    if not message.startswith(f"@{BOT_USERNAME}"):
        return

    # Remove the bot username from the message
    query = message[len(f"@{BOT_USERNAME}"):].strip()

    if not query:
        await update.message.reply_text("Please ask a question after mentioning me!")
        return

    # Store the query in Firebase
    await store_user_query(
        user_id=update.effective_user.id,
        command="nlp",
        query=query
    )

    # Process the query using OpenAI
    response = await process_nlp_query(query)

    await update.message.reply_text(response)