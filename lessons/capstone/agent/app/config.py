"""Settings from environment variables (docker-compose passes them from .env)."""

import os

FOUNDRY_BASE_URL = os.environ.get("FOUNDRY_BASE_URL", "")  # https://<resource>.openai.azure.com/openai/v1/
FOUNDRY_MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-5.4-mini")  # a reasoning model (BYOK always sends effort)
FOUNDRY_SCOPE = "https://cognitiveservices.azure.com/.default"

DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "checkout")
DB_RO_DSN = f"host={DB_HOST} dbname={DB_NAME} user=app_ro password={os.environ.get('APP_RO_PASSWORD', '')}"
DB_RW_DSN = f"host={DB_HOST} dbname={DB_NAME} user=app_rw password={os.environ.get('APP_RW_PASSWORD', '')}"

APPINSIGHTS = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
TURN_TIMEOUT_S = float(os.environ.get("TURN_TIMEOUT_S", "300"))
MAX_AI_CREDITS = float(os.environ.get("MAX_AI_CREDITS", "100"))  # Lesson 13 (minimum is 30)

CLIENT_INFO = {"application_name": "checkout-investigator", "application_version": "1.0.0"}
