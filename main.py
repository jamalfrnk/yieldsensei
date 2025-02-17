import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_handlers import (
    start_command,
    help_command,
    price_command,
    market_command,
    technical_command,
    signal_command,
    news_command,
    handle_message,
    BOT_USERNAME
)
from config import TELEGRAM_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f'Update "{update}" caused error "{context.error}"')

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_TOKEN provided")
        return

    # Create the Application with the builder pattern
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers with username prefix requirement
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("technical", technical_command))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("news", news_command))

    # Add message handler for NLP with username prefix requirement
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f"^@{BOT_USERNAME}"),
        handle_message
    ))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
