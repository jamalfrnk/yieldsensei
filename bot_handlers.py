import logging
import re
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
@yieldsensei_bot /signal <token_or_address> - Get detailed trading signal analysis
Examples:
• /signal btc - Analysis for Bitcoin
• /signal 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr - Analysis by contract address

ℹ️ General Commands:
@yieldsensei_bot /help - Show this help message
@yieldsensei_bot /start - Get started with Yield Sensei
"""

def is_contract_address(input_str: str) -> bool:
    """Check if the input looks like a contract address."""
    # Basic validation for common address formats (ETH, SOL, etc.)
    return len(input_str) >= 32 and not input_str.isdigit()

def get_command_suggestion(error_message: str) -> str:
    """Get a helpful command suggestion based on the error."""
    suggestions = {
        "not found in our database": "Try using a valid token symbol (e.g., '/signal btc') or contract address (e.g., '/signal 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr')",
        "Unable to fetch market data": "The API is temporarily unavailable. Please try again in a few minutes",
        "Unable to process market data": "There might be an issue with the token data. Try using a different token or wait a few minutes",
        "No price data available": "This token might be too new or not actively traded. Try using a more established token",
        "Network connectivity issue": "Connection issues detected. Please try again in a few moments",
        "Invalid or unsupported contract": "Make sure you're using a valid contract address or try using the token symbol instead"
    }

    for error_pattern, suggestion in suggestions.items():
        if error_pattern.lower() in error_message.lower():
            return f"💡 Suggestion: {suggestion}"

    return "💡 Suggestion: Make sure you're using the correct command format. Type /help to see examples"

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
@cache
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed trading signal analysis for token symbol or contract address."""
    if not context.args:
        help_message = (
            "Please provide a token symbol or contract address.\n"
            "Examples:\n"
            "• /signal btc - Analysis for Bitcoin\n"
            "• /signal 7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr - Analysis by contract address"
        )
        logger.info("Signal command called without arguments")
        try:
            await update.message.reply_text(help_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=help_message)
        return

    token_input = context.args[0].lower()
    logger.info(f"Processing signal analysis for input: {token_input}")

    try:
        logger.info(f"Fetching signal analysis data")

        # If it looks like a contract address, try to get token info first
        if is_contract_address(token_input):
            logger.info("Input appears to be a contract address, fetching token data first")
            token_data = await get_token_pairs(token_input)
            if not token_data or "pairs" not in token_data or not token_data["pairs"]:
                raise ValueError("Invalid or unsupported contract address")
            # Use the token symbol from DEX data for analysis
            token_input = token_data["pairs"][0].get("baseToken", {}).get("symbol", "").lower()
            logger.info(f"Resolved contract address to token symbol: {token_input}")

        signal_data = await get_signal_analysis(token_input)
        logger.info(f"Successfully retrieved signal analysis")

        message = (
            f"🎯 Trading Signal Analysis for {token_input.upper()}\n\n"
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

        logger.info(f"Sending signal analysis response")
        try:
            await update.message.reply_text(message)
            logger.info(f"Successfully sent signal analysis")
        except Exception as e:
            logger.error(f"Failed to send message via update.message: {str(e)}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            logger.info(f"Successfully sent signal analysis via context.bot")

    except Exception as e:
        error_message = f"Error getting signal analysis: {str(e)}"
        suggestion = get_command_suggestion(str(e))
        full_message = f"{error_message}\n\n{suggestion}"

        logger.error(f"Signal analysis failed: {str(e)}")
        try:
            await update.message.reply_text(full_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=full_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages that are not commands."""
    message = update.message.text

    # Check if message starts with @yieldsensei_bot
    if not message.startswith(f"@{BOT_USERNAME}"):
        return

    # Remove the bot username from the message
    query = message[len(f"@{BOT_USERNAME}"):].strip()

    if not query:
        suggestion = (
            "Please provide a command after mentioning me!\n\n"
            "💡 Try these commands:\n"
            "• /help - See all available commands\n"
            "• /signal btc - Get Bitcoin analysis\n"
            "• /price eth - Get Ethereum price"
        )
        try:
            await update.message.reply_text(suggestion)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=suggestion)
        return

    suggestion = (
        "Command not recognized.\n\n"
        "💡 Available commands:\n"
        "• /help - See all commands\n"
        "• /signal <token/address> - Get trading signals\n"
        "• /price <token> - Get token price\n"
        "• /market <token> - Get market data\n"
        "• /dexinfo <address> - Get DEX information"
    )
    try:
        await update.message.reply_text(suggestion)
    except Exception:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=suggestion)