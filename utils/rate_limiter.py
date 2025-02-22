from functools import wraps
import time
from collections import defaultdict
from config import RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD, ERROR_RATE_LIMIT

# Store user calls with timestamps
user_calls = defaultdict(list)

def rate_limit(func=None, *, error_message=None):
    """Rate limiting decorator with custom error messages."""
    if func is None:
        return lambda f: rate_limit(f, error_message=error_message)

    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        current_time = time.time()

        # Remove old timestamps
        user_calls[user_id] = [
            timestamp for timestamp in user_calls[user_id]
            if current_time - timestamp < RATE_LIMIT_PERIOD
        ]

        # Check if user has exceeded rate limit
        if len(user_calls[user_id]) >= RATE_LIMIT_CALLS:
            # Calculate wait time
            oldest_call = min(user_calls[user_id])
            wait_time = int(RATE_LIMIT_PERIOD - (current_time - oldest_call))

            # Use custom error message if provided, otherwise use default
            if error_message:
                from bot_handlers import format_wait_time
                message = error_message.format(wait_time=format_wait_time(wait_time))
            else:
                message = ERROR_RATE_LIMIT

            await update.message.reply_text(message)
            return

        # Add current timestamp
        user_calls[user_id].append(current_time)

        return await func(update, context, *args, **kwargs)
    return wrapper