import os
import logging
import asyncio
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

async def shutdown(application):
    """Shut down the bot gracefully."""
    await application.stop()
    await application.shutdown()

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_TOKEN provided")
        return

    try:
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
        application.add_handler(CommandHandler("dexinfo", dexinfo_command))
        application.add_handler(CommandHandler("dexsearch", dexsearch_command))

        # Add message handler for NLP with username prefix requirement
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(f"^@{BOT_USERNAME}"),
            handle_message
        ))

        # Register error handler
        application.add_error_handler(error_handler)

        # Start the Bot with proper shutdown handling
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        if 'application' in locals():
            asyncio.run(shutdown(application))

if __name__ == '__main__':
    main()