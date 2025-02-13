from functools import wraps
import time
from collections import defaultdict
from config import RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD, ERROR_RATE_LIMIT

# Store user calls with timestamps
user_calls = defaultdict(list)

def rate_limit(func):
    """Rate limiting decorator."""
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
            await update.message.reply_text(ERROR_RATE_LIMIT)
            return
        
        # Add current timestamp
        user_calls[user_id].append(current_time)
        
        return await func(update, context, *args, **kwargs)
    return wrapper
