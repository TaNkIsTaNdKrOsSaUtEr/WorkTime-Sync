# WorkTimeSync/tests/test_services.py
"""
Юнит-тесты для сервисов.
"""
from datetime import date, timedelta
from services.analytics import calculate_metrics
from services.recommendation import generate_recommendations
from services.export import generate_excel_report
from models import WorkEntry, CalendarEvent, AbsenceRequest, AbsenceType, AbsenceStatus
from datetime import time

def test_calculate_metrics_no_data(db_session, seed_data):
    """Пустой профиль – метрики должны быть по умолчанию."""
    user = seed_data["employee"]
    metrics = calculate_metrics(db_session, user)
    assert metrics["Ai"] == 1.0  # обновлено сегодня
    assert metrics["Li"] == 0.0
    assert metrics["Ci"] == 0.0

def test_calculate_metrics_with_overload(db_session, seed_data):
    """Сотрудник с перегрузкой."""
    user = seed_data["employee"]
    # Добавляем записи за последние 7 дней, сумма 70 часов
    for i in range(7):
        day = date.today() - timedelta(days=i)
        if day.weekday() < 5:  # рабочие дни
            db_session.add(WorkEntry(user_id=user.id, project_id=seed_data["project"].id, hours=10, date=day))
    db_session.commit()
    metrics = calculate_metrics(db_session, user)
    assert metrics["Li"] > 0.8  # перегруз

def test_generate_recommendations(db_session, seed_data):
    """Должны появиться рекомендации при дисбалансе."""
    manager = seed_data["manager"]
    employee = seed_data["employee"]
    # Иван – 10 часов в день, Мария – 2 часа (но у нас один сотрудник, поэтому добавим ещё одного)
    # Создадим второго сотрудника
    from models import User, RoleEnum, WorkFormat
    emp2 = User(
        full_name="Second Employee", username="emp2",
        hashed_password="123", role=RoleEnum.employee,
        team_id=manager.team_id,
        work_start=time(9,0), work_end=time(18,0),
        timezone="Europe/Moscow", work_format=WorkFormat.office,
        last_updated=date.today()
    )
    db_session.add(emp2)
    db_session.commit()
    # Добавим записи
    for i in range(5):
        day = date.today() - timedelta(days=i)
        db_session.add(WorkEntry(user_id=employee.id, project_id=seed_data["project"].id, hours=10, date=day))
        db_session.add(WorkEntry(user_id=emp2.id, project_id=seed_data["project"].id, hours=1, date=day))
    db_session.commit()
    recs = generate_recommendations(db_session, manager.team_id)
    assert len(recs) > 0

def test_export_excel(db_session, seed_data):
    """Экспорт Excel не должен падать."""
    stream = generate_excel_report(db_session)
    assert stream.read(4)[:2] == b'PK'  # сигнатура ZIP (xlsx)

    