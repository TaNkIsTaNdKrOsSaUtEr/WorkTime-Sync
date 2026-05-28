# WorkTimeSync/Dockerfile
FROM python:3.12-slim

# Установка системных зависимостей (для сборки библиотек)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём пустую директорию static (если не существует) и базу данных
RUN mkdir -p static && touch static/favicon.ico

# Инициализация базы и демо-данных
RUN python init_db.py && python fill_demo_data.py

# Открываем порт
EXPOSE 8000

# Запуск сервера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]