# WorkTimeSync/routers/auth_router.py
"""
Маршруты аутентификации: веб-логин и API-токен.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form  # основные инструменты FastAPI: маршрутизатор, зависимости, исключения, HTTP-статусы, объект запроса, данные формы
from fastapi.responses import HTMLResponse, RedirectResponse  # типы ответов: HTML-страница и редирект
from fastapi.security import OAuth2PasswordRequestForm  # стандартная форма OAuth2 для получения токена (используется в Swagger)
from sqlalchemy.orm import Session  # тип сессии SQLAlchemy
from database import get_db  # зависимость для получения сессии БД
from models import User, RoleEnum  # модель пользователя и перечисление ролей
from auth import verify_password, get_password_hash, create_access_token  # функции аутентификации: проверка пароля, хеширование, создание JWT
from fastapi.templating import Jinja2Templates  # шаблонизатор Jinja2 для рендера HTML

router = APIRouter()  # создаём экземпляр маршрутизатора для группировки эндпоинтов
templates = Jinja2Templates(directory="templates")  # указываем папку с HTML-шаблонами

@router.get("/login", response_class=HTMLResponse)  # GET-запрос на /auth/login – страница входа
def login_page(request: Request):  # параметр request обязателен для Jinja2
    return templates.TemplateResponse("login.html", {"request": request})  # рендерим шаблон login.html, передаём request

@router.post("/login")  # POST-запрос на /auth/login – обработка формы входа
def login_post(request: Request,  # объект запроса
                username: str = Form(""),  # поле "username" из формы (по умолчанию пустая строка)
                password: str = Form(""),  # поле "password" из формы
                db: Session = Depends(get_db)):  # сессия БД внедряется автоматически
    # Отладочный вывод
    print(f"=== LOGIN ATTEMPT ===")  # отладочное сообщение в консоль сервера
    print(f"Username received: '{username}'")  # выводим полученный логин
    print(f"Password received: '{password}'")  # выводим полученный пароль (только для отладки, в продакшене убрать!)

    user = db.query(User).filter(User.username == username).first()  # ищем пользователя по логину в БД
    if not user:  # если пользователь не найден
        print("User not found")  # отладочный вывод
    else:  # если пользователь найден
        valid = verify_password(password, user.hashed_password)  # проверяем пароль через bcrypt
        print(f"Password valid: {valid}")  # выводим результат проверки

    if not user or not verify_password(password, user.hashed_password):  # если пользователь не найден ИЛИ пароль неверный
        print("Returning error page")  # отладка
        return templates.TemplateResponse("login.html", {  # возвращаем ту же страницу входа
            "request": request,  # объект запроса
            "error": "Неверный логин или пароль"  # сообщение об ошибке для отображения
        })
    access_token = create_access_token(data={"sub": str(user.id)})  # создаём JWT-токен, в payload кладём ID пользователя
    response = RedirectResponse(url="/dashboard/", status_code=status.HTTP_303_SEE_OTHER)  # готовим редирект на дашборд (303 See Other)
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=86400)  # ставим httpOnly куку с токеном на 24 часа
    print("Login successful, redirecting to /dashboard/")  # отладка
    return response  # возвращаем ответ с редиректом и установленной кукой

# OAuth2 endpoint (для Swagger)
@router.post("/token")  # POST-запрос на /auth/token – получение JWT через OAuth2 (для Swagger UI и API)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),  # данные формы OAuth2 (username, password)
                           db: Session = Depends(get_db)):  # сессия БД
    user = db.query(User).filter(User.username == form_data.username).first()  # ищем пользователя по логину из формы
    if not user or not verify_password(form_data.password, user.hashed_password):  # если не найден или пароль не совпал
        raise HTTPException(  # выбрасываем исключение
            status_code=status.HTTP_401_UNAUTHORIZED,  # код 401 Unauthorized
            detail="Неверный логин или пароль",  # сообщение
            headers={"WWW-Authenticate": "Bearer"},  # заголовок для OAuth2
        )
    access_token = create_access_token(data={"sub": str(user.id)})  # создаём токен
    return {"access_token": access_token, "token_type": "bearer"}  # возвращаем JSON с токеном (стандарт OAuth2)

# Регистрация и выход остаются без изменений
@router.get("/register", response_class=HTMLResponse)  # GET-запрос на /auth/register – страница регистрации
def register_page(request: Request):  # объект запроса
    return templates.TemplateResponse("register.html", {"request": request})  # рендерим шаблон регистрации

@router.post("/register")  # POST-запрос на /auth/register – обработка формы регистрации
def register_post(request: Request,  # объект запроса
                  full_name: str = Form(...),  # полное имя (обязательное поле)
                  username: str = Form(...),  # логин (обязательное)
                  password: str = Form(...),  # пароль (обязательное)
                  role: str = Form("employee"),  # роль (по умолчанию employee)
                  db: Session = Depends(get_db)):  # сессия БД
    if db.query(User).filter(User.username == username).first():  # проверяем, существует ли уже такой логин
        return templates.TemplateResponse("register.html", {"request": request, "error": "Пользователь уже существует"})  # если да – возвращаем ошибку на странице
    try:
        role_enum = RoleEnum(role)  # пробуем преобразовать строку в Enum RoleEnum
    except ValueError:  # если невалидная роль
        role_enum = RoleEnum.employee  # назначаем employee по умолчанию
    user = User(  # создаём объект нового пользователя
        full_name=full_name,  # полное имя
        username=username,  # логин
        hashed_password=get_password_hash(password),  # хешируем пароль
        role=role_enum  # роль
    )
    db.add(user)  # добавляем пользователя в сессию БД
    db.commit()  # фиксируем изменения
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)  # редирект на страницу входа

@router.get("/logout")  # GET-запрос на /auth/logout – выход из системы
def logout():
    response = RedirectResponse(url="/auth/login")  # готовим редирект на страницу входа
    response.delete_cookie("access_token")  # удаляем куку с токеном
    return response  # возвращаем ответ
    