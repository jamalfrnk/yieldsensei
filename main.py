import logging
import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_handlers import (
    start_command, help_command, price_command, market_command,
    signal_command, dexinfo_command, handle_message, BOT_USERNAME
)
from config import TELEGRAM_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context):
    """Log Errors caused by Updates."""
    try:
        if update:
            logger.error(f'Update "{update}" caused error "{context.error}"')
        else:
            logger.error(f'Error occurred: {context.error}')
    except Exception as e:
        logger.error(f'Error in error handler: {e}')

def main():
    """Start the bot."""
    try:
        if not TELEGRAM_TOKEN:
            raise ValueError("No TELEGRAM_TOKEN provided")

        # Create the Application with specific settings to prevent multiple instances
        application = Application.builder().token(TELEGRAM_TOKEN).concurrent_updates(False).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("price", price_command))
        application.add_handler(CommandHandler("market", market_command))
        application.add_handler(CommandHandler("signal", signal_command))
        application.add_handler(CommandHandler("dexinfo", dexinfo_command))

        # Register message handler for non-command messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Register error handler
        application.add_error_handler(error_handler)

        logger.info("Starting bot...")
        # Use drop_pending_updates to prevent multiple instances from processing the same updates
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")
        sys.exit(1)