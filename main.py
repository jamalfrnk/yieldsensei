import logging
import os
import sys
try:
    from telegram import Update
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes
    )
except ImportError:
    logging.error("Failed to import telegram modules. Make sure python-telegram-bot is installed.")
    sys.exit(1)

from bot_handlers import (
    start_command, help_command, price_command, market_command,
    signal_command, dexinfo_command, handle_message, BOT_USERNAME
)
from config import TELEGRAM_TOKEN

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('yieldsensei.log')
    ]
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context):
    """Log Errors caused by Updates."""
    try:
        if update:
            logger.error(f'Update "{update}" caused error "{context.error}"')
            if context.error and hasattr(context.error, '__traceback__'):
                logger.error(f'Full traceback: {context.error.__traceback__}')
        else:
            logger.error(f'Error occurred: {context.error}')
    except Exception as e:
        logger.error(f'Error in error handler: {e}')

def main():
    """Start the bot."""
    try:
        if not TELEGRAM_TOKEN:
            raise ValueError("No TELEGRAM_TOKEN provided")

        logger.info(f"Initializing bot with username: {BOT_USERNAME}")

        # Create the Application with specific settings
        application = Application.builder().token(TELEGRAM_TOKEN).concurrent_updates(True).build()

        # Add command handlers with logging
        logger.info("Registering command handlers...")
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("price", price_command))
        application.add_handler(CommandHandler("market", market_command))
        application.add_handler(CommandHandler("signal", signal_command))
        application.add_handler(CommandHandler("dexinfo", dexinfo_command))
        logger.info("Command handlers registered successfully")

        # Register message handler for non-command messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Message handler registered")

        # Register error handler
        application.add_error_handler(error_handler)
        logger.info("Error handler registered")

        logger.info("Starting bot polling...")
        # Use drop_pending_updates to prevent multiple instances from processing the same updates
        application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Critical error during bot initialization: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    try:
        logger.info("Bot script started")
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}", exc_info=True)
        sys.exit(1)