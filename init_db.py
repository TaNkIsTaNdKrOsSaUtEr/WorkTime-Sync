# WorkTimeSync/init_db.py
"""
Скрипт для первоначального создания таблиц и наполнения тестовыми данными.
"""
from database import engine, Base, SessionLocal
from models import Team, User, RoleEnum, Project, WorkFormat
from auth import get_password_hash
from datetime import date, time

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if not db.query(Team).first():
    team = Team(name="Разработка")
    db.add(team)
    db.commit()

    # HR
    hr = User(full_name="Анна HR", username="hr", hashed_password=get_password_hash("123"),
              role=RoleEnum.hr, work_start=time(9,0), work_end=time(18,0),
              timezone="Europe/Moscow", work_format=WorkFormat.office, last_updated=date.today())
    db.add(hr)

    # Руководитель
    manager = User(full_name="Сергей Руководитель", username="manager", hashed_password=get_password_hash("123"),
                   role=RoleEnum.manager, team_id=team.id,
                   work_start=time(9,0), work_end=time(18,0),
                   timezone="Europe/Moscow", work_format=WorkFormat.office, last_updated=date.today())
    db.add(manager)
         # Проектный менеджер
    pm = User(full_name="Виктор ПМ", username="pm", hashed_password=get_password_hash("123"),
              role=RoleEnum.project_manager, team_id=team.id,
              work_start=time(9,0), work_end=time(18,0),
              timezone="Europe/Moscow", work_format=WorkFormat.hybrid, last_updated=date.today())
    db.add(pm)

    # Аналитик
    analyst = User(full_name="Инна Аналитик", username="analyst", hashed_password=get_password_hash("123"),
                   role=RoleEnum.analyst, team_id=team.id,
                   work_start=time(9,0), work_end=time(18,0),
                   timezone="Europe/Moscow", work_format=WorkFormat.office, last_updated=date.today())
    db.add(analyst)
    
    # Сотрудники (8 человек, включая старых)
    employees = [
        User(full_name="Иван Сотрудник", username="ivan", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(9,0), work_end=time(18,0), timezone="Europe/Moscow",
             work_format=WorkFormat.office, last_updated=date.today()),
        User(full_name="Мария Сотрудник", username="maria", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(10,0), work_end=time(19,0), timezone="Europe/Moscow",
             work_format=WorkFormat.remote, last_updated=date.today()),
        User(full_name="Алексей Петров", username="alex", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(8,0), work_end=time(17,0), timezone="Asia/Yekaterinburg",
             work_format=WorkFormat.hybrid, last_updated=date.today()),
        User(full_name="Ольга Смирнова", username="olga", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(9,0), work_end=time(18,0), timezone="Europe/Moscow",
             work_format=WorkFormat.office, last_updated=date.today()),
        User(full_name="Дмитрий Козлов", username="dmitry", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(11,0), work_end=time(20,0), timezone="Europe/Moscow",
             work_format=WorkFormat.remote, last_updated=date.today()),
        User(full_name="Елена Новикова", username="elena", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(9,0), work_end=time(18,0), timezone="Europe/Moscow",
             work_format=WorkFormat.hybrid, last_updated=date.today()),
        User(full_name="Павел Морозов", username="pavel", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(7,0), work_end=time(16,0), timezone="Europe/Moscow",
             work_format=WorkFormat.office, last_updated=date.today()),
        User(full_name="Татьяна Федорова", username="tatiana", hashed_password=get_password_hash("123"),
             role=RoleEnum.employee, team_id=team.id,
             work_start=time(9,0), work_end=time(18,0), timezone="Europe/Moscow",
             work_format=WorkFormat.remote, last_updated=date.today()),
    ]
    db.add_all(employees)
    db.commit()

    # Проект
    project = Project(name="WorkTime Sync", manager_id=manager.id)
    db.add(project)
    db.commit()

db.close()
print("База данных инициализирована с 8 сотрудниками.")

