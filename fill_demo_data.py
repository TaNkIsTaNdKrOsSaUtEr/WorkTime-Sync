# WorkTimeSync/fill_demo_data.py
"""
Генератор тестовых записей рабочего времени и календарных событий.
"""
from database import SessionLocal
from models import User, WorkEntry, Project, CalendarEvent
from datetime import date, timedelta, time
import random

db = SessionLocal()

# Находим сотрудников и проект
employees = db.query(User).filter(User.role == "employee").all()
manager = db.query(User).filter(User.username == "manager").first()
project = db.query(Project).first()

if not all([employees, manager, project]):
    print("Сначала запустите init_db.py")
    db.close()
    exit()

# Очищаем старые записи
db.query(WorkEntry).delete()
db.query(CalendarEvent).delete()

today = date.today()
# Генерируем данные за последние 2 недели
for days_ago in range(14, 0, -1):
    day = today - timedelta(days=days_ago)
    if day.weekday() >= 5:  # выходные
        continue

    for emp in employees:
        # Рабочие часы (разная загрузка)
        if emp.username in ["ivan", "alex"]:
            hours = random.uniform(8.5, 12.0)
        elif emp.username == "maria":
            hours = random.uniform(1.0, 3.5)
        else:
            hours = random.uniform(4, 8)
        db.add(WorkEntry(user_id=emp.id, project_id=project.id, hours=round(hours, 1), date=day))

        # Календарные события (2-4 события в день с вероятностью 0.7)
        if random.random() < 0.7:
            num_events = random.randint(1, 3)
            for _ in range(num_events):
                # Случайное время начала от 8 до 20 часов
                start_hour = random.randint(8, 20)
                start_minute = random.randint(0, 3) * 15
                duration = random.choice([30, 60, 90])
                start_time = time(start_hour, start_minute)
                end_hour = start_hour + (start_minute + duration) // 60
                end_minute = (start_minute + duration) % 60
                if end_hour > 23:
                    end_hour = 23
                    end_minute = 59
                end_time = time(end_hour, end_minute)
                db.add(CalendarEvent(
                    user_id=emp.id,
                    start_time=start_time,
                    end_time=end_time,
                    event_date=day,
                    event_type=random.choice(["meeting", "task", "review"])
                ))

    # Руководитель
    if random.random() < 0.6:
        db.add(WorkEntry(user_id=manager.id, project_id=project.id,
                         hours=round(random.uniform(4, 8), 1), date=day))

db.commit()
db.close()
print("Демо-данные с событиями созданы.")


