from sqlalchemy import create_engine  # импорт функции для создания подключения к БД
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # sessionmaker – фабрика сессий, DeclarativeBase – базовый класс для моделей
from config import DATABASE_URL  # строка подключения к БД из настроек

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # создаём движок SQLAlchemy; для SQLite отключаем проверку того же потока (нужно для FastAPI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # фабрика сессий: без автокоммита, без автосброса, привязана к нашему движку

class Base(DeclarativeBase):  # базовый класс для всех ORM-моделей (наследуемся от DeclarativeBase)
    pass  # пустой – все в родительском классе

def get_db():  # функция-зависимость FastAPI, которая будет выдавать сессию БД
    """Зависимость FastAPI для получения сессии БД."""
    db = SessionLocal()  # создаём новую сессию
    try:
        yield db  # отдаём сессию тому, кто вызвал (роутеру)
    finally:
        db.close()  # гарантированно закрываем сессию после завершения запроса