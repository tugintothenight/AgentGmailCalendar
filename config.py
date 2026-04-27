import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
AUTO_CHECK_MAIL = False
GAP_AUTO_RUN = 30 # Phút

# OpenRouter API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = "meta-llama/llama-3.3-70b-instruct"
JUDGE_MODEL = "meta-llama/llama-3-8b-instruct"

# OpenRouter Base URL
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Security Settings
MAX_TOTAL_LOOPS = 10
MAX_DUPLICATE_ACTIONS = 3
ALLOWED_TOOLS = ["fetch_raw_emails", "schedule_event", "hydradb_store", "hydradb_retrieve"]
SENSITIVE_TOOLS = ["send_email", "schedule_event", "delete_schedules"]

# DLP Settings
ENABLE_DLP_FILTER = True

# Database
DB_FILE = os.path.join(BASE_DIR, "data", "hydradb_storage.json")

# Google
GOOGLE_CREDS_PATH = os.path.join(BASE_DIR, "auth", "credentials.json")
GOOGLE_TOKEN_PATH = os.path.join(BASE_DIR, "auth", "token.json")
