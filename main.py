import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot_handlers import (
    start_command, help_command, price_command, market_command,
    technical_command, signal_command, news_command, handle_message,
    dexinfo_command, dexsearch_command, trending_command,
    setalert_command, removealert_command, BOT_USERNAME
)
from services.dexscreener_service import check_price_alerts
from config import TELEGRAM_TOKEN

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store active chat IDs for alerts
active_chats = set()

async def check_alerts_loop(context):
    """Background task to check price alerts."""
    try:
        triggered_alerts = await check_price_alerts()
        for alert in triggered_alerts:
            direction = "above" if alert["is_above"] else "below"
            message = (
                f"🚨 Price Alert Triggered!\n\n"
                f"Token: {alert['token_name']}\n"
                f"Target: ${alert['target_price']}\n"
                f"Current Price: ${alert['current_price']}\n"
                f"Direction: {direction}\n\n"
                f"Use /dexinfo {alert['token_address']} for more details"
            )
            # Send alert to all active chats
            for chat_id in active_chats:
                try:
                    await context.bot.send_message(chat_id=chat_id, text=message)
                except Exception as e:
                    logger.error(f"Failed to send alert to chat {chat_id}: {e}")
                    active_chats.discard(chat_id)  # Remove inactive chat
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")


def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.error(f'Update "{update}" caused error "{context.error}"')

async def setup_application():
    """Initialize and configure the application."""
    if not TELEGRAM_TOKEN:
        raise ValueError("No TELEGRAM_TOKEN provided")

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Track active chats
    async def track_chat(update: Update, context):
        if update.effective_chat:
            active_chats.add(update.effective_chat.id)
        await start_command(update, context)

    # Add command handlers
    application.add_handler(CommandHandler("start", track_chat))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("technical", technical_command))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("dexinfo", dexinfo_command))
    application.add_handler(CommandHandler("dexsearch", dexsearch_command))
    application.add_handler(CommandHandler("trending", trending_command))
    application.add_handler(CommandHandler("setalert", setalert_command))
    application.add_handler(CommandHandler("removealert", removealert_command))

    # Add message handler for NLP
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(f"^@{BOT_USERNAME}"),
        handle_message
    ))

    # Register error handler
    application.add_error_handler(error_handler)

    return application

if __name__ == '__main__':
    try:
        # Create and configure the application
        app = asyncio.run(setup_application())

        # Start background alert checker
        app.job_queue.run_repeating(check_alerts_loop, interval=60)

        # Start the bot
        logger.info("Starting bot...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {e}")