from functools import wraps
import time
from config import CACHE_EXPIRY

# Cache storage
cache_store = {}

def cache(func):
    """Caching decorator."""
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        # Create cache key from command and arguments
        cache_key = f"{func.__name__}:{':'.join(context.args)}"
        current_time = time.time()
        
        # Check if cached result exists and is still valid
        if cache_key in cache_store:
            result, timestamp = cache_store[cache_key]
            if current_time - timestamp < CACHE_EXPIRY:
                return await update.message.reply_text(result)
        
        # Execute function and cache result
        response = await func(update, context, *args, **kwargs)
        if hasattr(update.message, 'text'):
            cache_store[cache_key] = (update.message.text, current_time)
        
        return response
    return wrapper
