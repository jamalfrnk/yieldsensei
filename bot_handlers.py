import logging
import re
from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, Application
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
🎯 Yield Sensei Bot Commands:

📊 Price & Market Data:
/price <token> - Get current price (e.g., /price btc)
/market <token> - Get market stats (e.g., /market eth)

🔍 Analysis:
/signal <token> - Get trading signals (e.g., /signal btc)
/dexinfo <address> - Get DEX pair info

ℹ️ Help:
/help - Show this menu
/start - Get started

Example usage:
• /signal btc - Bitcoin analysis
• /price eth - Ethereum price
• /market sol - Solana market data

⚠️ All predictions are AI-powered estimates. Always DYOR!
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
    try:
        logger.info(f"Start command received from user: {update.effective_user.id}")
        await update.message.reply_text(
            "Welcome to Yield Sensei! 🚀\n\n"
            "I'm your DeFi assistant, ready to help you with:\n"
            "• Real-time crypto prices 💰\n"
            "• Market data and analysis 📊\n"
            "• DEX pair information 🔍\n\n"
            f"Use /help to see all available commands."
        )
        logger.info(f"Start command response sent successfully to user: {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    try:
        logger.info(f"Help command received from user: {update.effective_user.id}")
        await update.message.reply_text(HELP_TEXT)
        logger.info(f"Help command response sent successfully to user: {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}", exc_info=True)
        await update.message.reply_text("An error occurred. Please try again later.")

# Update the rate limit error messages
RATE_LIMIT_MESSAGES = {
    "default": "🚦 Trading cooldown in effect! Please wait {wait_time} before your next request.\n\n💡 Tip: Use this time to review your trading strategy or check our documentation.",
    "price": "💹 Market data request limit reached! Next update available in {wait_time}.\n\n💡 Tip: Try using /market for more comprehensive data when available.",
    "signal": "📊 Signal analysis cooldown active ({wait_time} remaining).\n\n💡 Pro tip: Use this time to review previous signals and set up your trading parameters.",
    "market": "📈 Market data cooling period ({wait_time} left).\n\n💡 Consider checking token pairs on DEX in the meantime with /dexinfo.",
    "dexinfo": "🔍 DEX data request limit reached. Next analysis in {wait_time}.\n\n💡 While waiting, you can check basic price info with /price."
}

def format_wait_time(seconds):
    """Convert seconds to a user-friendly time format."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

@rate_limit(error_message=RATE_LIMIT_MESSAGES["price"])
@cache
async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token price."""
    if not context.args:
        try:
            await update.message.reply_text("Please provide a token symbol. Example: /price btc")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a token symbol. Example: /price btc"
            )
        return

    token = context.args[0].lower()
    try:
        logger.info(f"Fetching price data for token: {token}")
        price_data = await get_token_price(token)

        if not price_data or not isinstance(price_data, dict):
            raise ValueError("Invalid price data received")

        change = price_data.get('usd_24h_change', 0.0)
        price = price_data.get('usd', 0.0)
        change_emoji = "🟢" if change >= 0 else "🔴"

        message = (
            f"💰 {token.upper()} Price Analysis\n\n"
            f"Current Price: ${price:,.2f}\n"
            f"24h Change: {change_emoji} {abs(change):.2f}%\n\n"
            f"Use /market {token} for more details"
        )

        try:
            await update.message.reply_text(message)
            logger.info(f"Successfully sent price data for {token}")
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    except Exception as e:
        error_message = f"Error getting price: {str(e)}"
        logger.error(f"Price command failed: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit(error_message=RATE_LIMIT_MESSAGES["market"])
@cache
async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed market data."""
    if not context.args:
        try:
            await update.message.reply_text("Please provide a token symbol. Example: /market btc")
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a token symbol. Example: /market btc"
            )
        return

    token = context.args[0].lower()
    try:
        logger.info(f"Fetching market data for token: {token}")
        market_data = await get_token_market_data(token)

        if not market_data or not isinstance(market_data, dict):
            raise ValueError("Invalid market data received")

        # Format large numbers with safe gets
        market_cap = f"${market_data.get('market_cap', 0):,.0f}"
        volume = f"${market_data.get('total_volume', 0):,.0f}"
        market_cap_rank = market_data.get('market_cap_rank', 'N/A')
        high_24h = market_data.get('high_24h', 0)
        low_24h = market_data.get('low_24h', 0)
        price_change = market_data.get('price_change_percentage_24h', 0)

        message = (
            f"📊 {token.upper()} Market Data\n\n"
            f"Market Cap: {market_cap}\n"
            f"Rank: #{market_cap_rank}\n"
            f"24h Volume: {volume}\n"
            f"24h High: ${high_24h:,.2f}\n"
            f"24h Low: ${low_24h:,.2f}\n"
            f"24h Change: {price_change:.2f}%\n\n"
            f"Use /dexinfo <token_address> for DEX details"
        )

        try:
            await update.message.reply_text(message)
            logger.info(f"Successfully sent market data for {token}")
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    except Exception as e:
        error_message = f"Error getting market data: {str(e)}"
        logger.error(f"Market command failed: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit(error_message=RATE_LIMIT_MESSAGES["dexinfo"])
@cache
async def dexinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get token information from DEXScreener."""
    if not context.args:
        help_message = f"🔍 Please provide a token address. Example: /dexinfo <address>"
        logger.info("DEX info command called without arguments")
        try:
            await update.message.reply_text(help_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=help_message)
        return

    token_address = context.args[0]
    try:
        logger.info(f"Fetching DEX data for address: {token_address}")
        data = await get_token_pairs(token_address)

        if not data or not isinstance(data, dict):
            error_message = "❌ Failed to fetch token data"
            logger.error(f"Invalid response format for token address: {token_address}")
            try:
                await update.message.reply_text(error_message)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            return

        if "error" in data:
            error_message = f"❌ {data['error']}"
            logger.error(f"API error for token address {token_address}: {data['error']}")
            try:
                await update.message.reply_text(error_message)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            return

        pairs = data.get("pairs", [])
        if not pairs:
            error_message = "❌ No DEX pairs found for this token."
            logger.warning(f"No pairs found for token address: {token_address}")
            try:
                await update.message.reply_text(error_message)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)
            return

        pair = pairs[0]  # Get the most relevant pair

        # Safely get values with defaults
        price_usd = pair.get("priceUsd", "N/A")
        price_change = pair.get("priceChange", {}).get("h24", "N/A")
        liquidity_usd = pair.get("liquidity", {}).get("usd", 0)
        volume_usd = pair.get("volume", {}).get("h24", 0)
        chain_id = pair.get("chainId", "N/A")
        dex_id = pair.get("dexId", "N/A")
        pair_address = pair.get("pairAddress", "N/A")

        change_emoji = "⚪️" if price_change == "N/A" else "🟢" if float(price_change) >= 0 else "🔴"

        message = (
            f"🔍 Token DEX Information\n\n"
            f"⛓️ Chain: {chain_id}\n"
            f"🏦 DEX: {dex_id}\n"
            f"💵 Price: ${price_usd}\n"
            f"{change_emoji} 24h Change: {price_change}%\n"
            f"💧 Liquidity: ${liquidity_usd:,.2f}\n"
            f"📊 24h Volume: ${volume_usd:,.2f}\n"
            f"🔗 Pair Address: {pair_address}"
        )

        logger.info(f"Successfully retrieved DEX data for {token_address}")
        try:
            await update.message.reply_text(message)
            logger.info("DEX info message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send message via update.message: {str(e)}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
            logger.info("DEX info message sent successfully via context.bot")

    except Exception as e:
        error_message = f"❌ Error processing request: {str(e)}"
        logger.error(f"DEX info command failed: {str(e)}", exc_info=True)
        try:
            await update.message.reply_text(error_message)
        except Exception:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message)

@rate_limit(error_message=RATE_LIMIT_MESSAGES["signal"])
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

    suggestion = (
        "Need help? Try these commands:\n\n"
        "💡 Available commands:\n"
        "• /help - See all commands\n"
        "• /signal btc - Get Bitcoin analysis\n"
        "• /price eth - Get Ethereum price\n"
        "• /market sol - Get Solana market data\n"
        "• /dexinfo <address> - Get DEX information"
    )
    try:
        await update.message.reply_text(suggestion)
    except Exception:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=suggestion)