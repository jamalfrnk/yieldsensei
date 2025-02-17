import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from services.coingecko_service import get_token_price, get_token_market_data
from services.dexscreener_service import get_token_pairs
from utils.rate_limiter import rate_limit
from utils.cache import cache
from services.technical_analysis import get_signal_analysis

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_USERNAME = "yieldsensei_bot"
HELP_TEXT = """
Welcome to Yield Sensei! 🎯 Here are the available commands:

📊 Market Data Commands:
@yieldsensei_bot /price <token> - Get current price and 24h change
@yieldsensei_bot /market <token> - Get market cap, volume, and 24h high/low

🔍 DEX Information:
@yieldsensei_bot /dexinfo <token_address> - Get detailed DEX pair info

📈 Trading Signals:
@yieldsensei_bot /signal <token> - Get detailed trading signal analysis

ℹ️ General Commands:
@yieldsensei_bot /help - Show this help message
@yieldsensei_bot /start - Get started with Yield Sensei
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to Yield Sensei! 🚀\n\n"
        "I'm your DeFi assistant, ready to help you with:\n"
        "• Real-time crypto prices 💰\n"
        "• Market data and analysis 📊\n"
        "• DEX pair information 🔍\n\n"
        f"Use /help to see all available commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(HELP_TEXT)

@rate_limit
@cache
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token price."""
    if not context.args:
        try:
            await update.message.reply_text(f"Please provide a token symbol. Example: @{BOT_USERNAME} /price btc")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Please provide a token symbol. Example: @{BOT_USERNAME} /price btc"
            )
        return

    token = context.args[0].lower()
    try:
        price_data = await get_token_price(token)
        change = price_data['usd_24h_change']
        change_emoji = "🟢" if change >= 0 else "🔴"

        try:
            await update.message.reply_text(
                f"💰 {token.upper()} Price Analysis\n\n"
                f"Current Price: ${price_data['usd']:,.2f}\n"
                f"24h Change: {change_emoji} {abs(change):.2f}%\n\n"
                f"Use @{BOT_USERNAME} /market {token} for more details"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"💰 {token.upper()} Price Analysis\n\n"
                f"Current Price: ${price_data['usd']:,.2f}\n"
                f"24h Change: {change_emoji} {abs(change):.2f}%\n\n"
                f"Use @{BOT_USERNAME} /market {token} for more details"
            )
    except Exception as e:
        error_message = f"Error getting price: {str(e)}"
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit
@cache
async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed market data."""
    if not context.args:
        try:
            await update.message.reply_text(f"Please provide a token symbol. Example: @{BOT_USERNAME} /market btc")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Please provide a token symbol. Example: @{BOT_USERNAME} /market btc"
            )
        return

    token = context.args[0].lower()
    try:
        market_data = await get_token_market_data(token)

        # Format large numbers
        market_cap = f"${market_data['market_cap']:,.0f}"
        volume = f"${market_data['total_volume']:,.0f}"

        try:
            await update.message.reply_text(
                f"📊 {token.upper()} Market Data\n\n"
                f"Market Cap: {market_cap}\n"
                f"Rank: #{market_data['market_cap_rank']}\n"
                f"24h Volume: {volume}\n"
                f"24h High: ${market_data['high_24h']:,.2f}\n"
                f"24h Low: ${market_data['low_24h']:,.2f}\n"
                f"24h Change: {market_data['price_change_percentage_24h']:.2f}%\n\n"
                f"Use @{BOT_USERNAME} /dexinfo <token_address> for DEX details"
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📊 {token.upper()} Market Data\n\n"
                f"Market Cap: {market_cap}\n"
                f"Rank: #{market_data['market_cap_rank']}\n"
                f"24h Volume: {volume}\n"
                f"24h High: ${market_data['high_24h']:,.2f}\n"
                f"24h Low: ${market_data['low_24h']:,.2f}\n"
                f"24h Change: {market_data['price_change_percentage_24h']:.2f}%\n\n"
                f"Use @{BOT_USERNAME} /dexinfo <token_address> for DEX details"
            )
    except Exception as e:
        error_message = f"Error getting market data: {str(e)}"
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit
@cache
async def dexinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token information from DEXScreener."""
    if not context.args:
        try:
            await update.message.reply_text(f"🔍 Please provide a token address. Example: @{BOT_USERNAME} /dexinfo <address>")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔍 Please provide a token address. Example: @{BOT_USERNAME} /dexinfo <address>"
            )
        return

    token_address = context.args[0]
    try:
        data = await get_token_pairs(token_address)
        if data is None:
            error_message = "❌ Failed to fetch token data"
            try:
                await update.message.reply_text(error_message)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            return

        if "error" in data:
            error_message = f"❌ {data['error']}"
            try:
                await update.message.reply_text(error_message)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            return

        pairs = data.get("pairs", [])
        if not pairs:
            try:
                await update.message.reply_text("❌ No DEX pairs found for this token.")
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ No DEX pairs found for this token."
                )
            return

        pair = pairs[0]  # Get the most relevant pair
        price_usd = pair.get("priceUsd", "N/A")
        price_change = pair.get("priceChange", {}).get("h24", "N/A")
        liquidity_usd = pair.get("liquidity", {}).get("usd", 0)
        volume_usd = pair.get("volume", {}).get("h24", 0)

        change_emoji = "⚪️" if price_change == "N/A" else "🟢" if float(price_change) >= 0 else "🔴"

        message = (
            f"🔍 Token DEX Information\n\n"
            f"⛓️ Chain: {pair.get('chainId', 'N/A')}\n"
            f"🏦 DEX: {pair.get('dexId', 'N/A')}\n"
            f"💵 Price: ${price_usd}\n"
            f"{change_emoji} 24h Change: {price_change}%\n"
            f"💧 Liquidity: ${liquidity_usd:,.2f}\n"
            f"📊 24h Volume: ${volume_usd:,.2f}\n"
            f"🔗 Pair Address: {pair.get('pairAddress', 'N/A')}"
        )

        try:
            await update.message.reply_text(message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    except Exception as e:
        error_message = f"❌ Error processing request: {str(e)}"
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages that are not commands."""
    message = update.message.text

    # Check if message starts with @yieldsensei_bot
    if not message.startswith(f"@{BOT_USERNAME}"):
        return

    # Remove the bot username from the message
    query = message[len(f"@{BOT_USERNAME}"):].strip()

    if not query:
        try:
            await update.message.reply_text("Please provide a command after mentioning me!")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a command after mentioning me!"
            )
        return

    try:
        await update.message.reply_text(f"Please use one of the available commands. Type /help to see the list of commands.")
    except Exception:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Please use one of the available commands. Type /help to see the list of commands."
        )


@rate_limit
@cache
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed trading signal analysis."""
    if not context.args:
        error_message = f"Please provide a token symbol. Example: @{BOT_USERNAME} /signal btc"
        logger.info(f"Signal command called without token symbol")
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
        return

    token = context.args[0].lower()
    logger.info(f"Processing signal analysis for token: {token}")

    try:
        logger.info(f"Fetching signal analysis data for {token}")
        signal_data = await get_signal_analysis(token)
        logger.info(f"Successfully retrieved signal analysis for {token}")

        message = (
            f"🎯 Trading Signal Analysis for {token.upper()}\n\n"
            f"Current Price: {signal_data['current_price']}\n\n"
            f"Signal: {signal_data['signal']}\n"
            f"Strength: {signal_data['signal_strength']:.1f}%\n"
            f"Trend: {signal_data['trend_direction']}\n\n"
            f"Technical Indicators:\n"
            f"• RSI: {signal_data['rsi']:.1f}\n"
            f"• MACD: {signal_data['macd_signal']}\n\n"
            f"Price Levels:\n"
            f"• Resistance 2: {signal_data['resistance_2']}\n"
            f"• Resistance 1: {signal_data['resistance_1']}\n"
            f"• Support 1: {signal_data['support_1']}\n"
            f"• Support 2: {signal_data['support_2']}\n\n"
            f"{signal_data['dca_recommendation']}\n\n"
            f"⚠️ This is not financial advice. Always DYOR and manage risks! 📚"
        )

        logger.info(f"Sending signal analysis response for {token}")
        try:
            await update.message.reply_text(message)
            logger.info(f"Successfully sent signal analysis for {token}")
        except Exception as e:
            logger.error(f"Failed to send message via update.message: {str(e)}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            logger.info(f"Successfully sent signal analysis via context.bot for {token}")
    except Exception as e:
        error_message = f"Error getting signal analysis: {str(e)}"
        logger.error(f"Signal analysis failed for {token}: {str(e)}")
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)