# WorkTimeSync/auth.py
"""
Модуль аутентификации: хеширование паролей, JWT, получение текущего пользователя.
Токен ищется сначала в заголовке Authorization, затем в куке access_token.
"""
from datetime import datetime, timedelta, timezone # импорт классов для работы с датой и временем (JWT)
from jose import JWTError, jwt # JWTError – исключение при невалидном токене, jwt – кодирование/декодирование
from fastapi import Depends, HTTPException, status, Request # инструменты FastAPI для зависимостей, ошибок, статусов и запроса
from fastapi.security import OAuth2PasswordBearer # схема аутентификации OAuth2 (для Swagger)
from sqlalchemy.orm import Session # сессия базы данных
from database import get_db # функция-зависимость для получения сессии БД
from models import User # модель пользователя
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES # настройки JWT
import bcrypt # библиотека для безопасного хеширования паролей

# Инициализация схемы OAuth2PasswordBearer: указываем URL получения токена, auto_error=False чтобы не ругался при отсутствии заголовка (токен можно взять из куки)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool: # Сравнивает открытый пароль с хешем, возвращает True при совпадении.
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8')) # сверка пароля и хеша 

def get_password_hash(password: str) -> str: # Генерирует хеш пароля с солью.
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8') # хеширование и декодирование в строку

def create_access_token(data: dict, expires_delta: timedelta | None = None): # Создаёт JWT-токен с временем истечения.
    to_encode = data.copy() # копируем переданные данные (обычно sub: user_id)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)) # Вычисляем время истечения: переданное или по умолчанию из конфига
    to_encode.update({"exp": expire}) # добавляем срок годности
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM) # Кодируем токен с использованием секретного ключа и алгоритма

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User: 
    """
    Извлекает токен из заголовка Authorization или из куки access_token,
    декодирует и возвращает пользователя.
    """
    
    # Стандартное исключение для неавторизованного доступа
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидные учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = None # переменная для токена
    
    # Проверяем заголовок Authorization на наличие Bearer-токена
    auth_header = request.headers.get("Authorization") # получаем заголовок
    if auth_header and auth_header.startswith("Bearer "): # если заголовок есть и начинается с 'Bearer '
        token = auth_header[len("Bearer "):] # извлекаем сам токен, отрезая префикс
    # Затем кука
    if not token:   # Если токен не найден в заголовке, ищем в куке access_token
        token = request.cookies.get("access_token") # получаем куку
    if not token:   # Если токена нет нигде, выбрасываем исключение
        raise credentials_exception

    try:
        # Декодируем токен, проверяем подпись и срок действия
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub") # извлекаем идентификатор пользователя
        if user_id is None: # если sub отсутствует — невалидный токен
            raise credentials_exception
    except JWTError: # любая ошибка JWT (неверная подпись, истёк срок и т.д.)
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first() # Ищем пользователя в базе по ID
    if user is None: # если пользователь не найден (удалён или не существует)
        raise credentials_exception
    return user # возвращаем объект User

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Возвращает текущего пользователя (доп. проверка, если нужна будет блокировка)."""
    return current_user
    