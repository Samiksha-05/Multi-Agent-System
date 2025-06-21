# utils/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

# Memory Store Configuration
USE_REDIS = os.getenv("USE_REDIS", "False").lower() in ("true", "1", "t")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
SQLITE_PATH = os.getenv("SQLITE_PATH", "./memory.db")

# Model Configuration
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./model_cache")
TEXT_CLASSIFIER_MODEL = os.getenv("TEXT_CLASSIFIER_MODEL", "distilbert-base-uncased")
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "app.log")