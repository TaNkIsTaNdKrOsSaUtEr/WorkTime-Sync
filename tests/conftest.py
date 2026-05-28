# WorkTimeSync/tests/conftest.py
"""
Фикстуры для тестов.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app
from models import Team, User, RoleEnum, WorkFormat, Project
from auth import get_password_hash
from datetime import date, time

# Подключаемся к SQLite в памяти для тестов
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_database():
    """Создаёт таблицы перед каждым тестом."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    """Возвращает новую сессию для тестов."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client():
    """FastAPI TestClient с переопределённой зависимостью БД."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def seed_data(db_session):
    """Заполняет базу тестовыми данными: команда, руководитель, сотрудник, HR."""
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.commit()

    manager = User(
        full_name="Manager Test", username="manager",
        hashed_password=get_password_hash("123"),
        role=RoleEnum.manager, team_id=team.id,
        work_start=time(9,0), work_end=time(18,0),
        timezone="Europe/Moscow", work_format=WorkFormat.office,
        last_updated=date.today()
    )
    employee = User(
        full_name="Employee Test", username="employee",
        hashed_password=get_password_hash("123"),
        role=RoleEnum.employee, team_id=team.id,
        work_start=time(10,0), work_end=time(19,0),
        timezone="Europe/Moscow", work_format=WorkFormat.remote,
        last_updated=date.today()
    )
    hr = User(
        full_name="HR Test", username="hr",
        hashed_password=get_password_hash("123"),
        role=RoleEnum.hr, team_id=None,
        work_start=time(9,0), work_end=time(18,0),
        timezone="Europe/Moscow", work_format=WorkFormat.office,
        last_updated=date.today()
    )
    db_session.add_all([manager, employee, hr])
    db_session.commit()

    project = Project(name="Test Project", manager_id=manager.id)
    db_session.add(project)
    db_session.commit()
    return {
        "manager": manager,
        "employee": employee,
        "hr": hr,
        "project": project
    }

def get_token(client, username, password="123"):
    """Возвращает токен для пользователя."""
    response = client.post("/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"Не удалось получить токен для {username}: {response.text}"
    return response.json()["access_token"]
