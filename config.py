"""
Централизованные настройки приложения.
"""
import os

# Секретный ключ для подписи JWT. В реальном проекте храните в переменных окружения.
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# Путь к базе SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./worktime.db")
