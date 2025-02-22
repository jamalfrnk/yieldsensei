import os

# API Keys and Tokens
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")

# CoinGecko API Configuration
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Rate Limiting Configuration
RATE_LIMIT_CALLS = int(os.environ.get("RATE_LIMIT_CALLS", "60"))
RATE_LIMIT_PERIOD = int(os.environ.get("RATE_LIMIT_PERIOD", "60"))  # in seconds

# Cache Configuration
CACHE_EXPIRY = int(os.environ.get("CACHE_EXPIRY", "300"))  # 5 minutes in seconds

# Error Messages
ERROR_RATE_LIMIT = "You've reached the rate limit. Please try again later."
ERROR_INVALID_TOKEN = "Invalid token symbol. Please try again."
ERROR_API_ERROR = "An error occurred while fetching data. Please try again."

# Production Settings
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")