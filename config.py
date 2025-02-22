import os
from dotenv import load_dotenv
import logging.config

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    # API Keys and Tokens
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Application Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

    # API Configuration
    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    # Rate Limiting Configuration
    RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "60"))
    RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "60"))  # in seconds

    # Cache Configuration
    CACHE_EXPIRY = int(os.getenv("CACHE_EXPIRY", "300"))  # 5 minutes in seconds

    # Error Messages
    ERROR_RATE_LIMIT = "You've reached the rate limit. Please try again later."
    ERROR_INVALID_TOKEN = "Invalid token symbol. Please try again."
    ERROR_API_ERROR = "An error occurred while fetching data. Please try again."

    @staticmethod
    def init_logging():
        """Initialize logging configuration"""
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'standard',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'level': 'INFO',
                    'formatter': 'standard',
                    'filename': 'yieldsensei.log',
                    'mode': 'a',
                },
            },
            'loggers': {
                '': {  # root logger
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG' if os.getenv("DEBUG", "False").lower() == "true" else 'INFO',
                    'propagate': True
                }
            }
        }
        logging.config.dictConfig(logging_config)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    ENVIRONMENT = "development"

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    ENVIRONMENT = "production"

# Create config dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

def get_config():
    """Get the appropriate configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    return config.get(env, config["default"])