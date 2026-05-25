# WorkTimeSync/services/analytics.py
"""
Сервис аналитики: расчёт показателей актуальности, конфликтов, загрузки.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, WorkEntry, CalendarEvent, AbsenceRequest
from datetime import date, timedelta, datetime
import numpy as np

MAX_DAYS_WITHOUT_UPDATE = 90  # D в формуле актуальности

def calculate_metrics(db: Session, user: User):
    """Возвращает словарь с метриками для одного сотрудника."""
    today = date.today()
    # 1. Дней с последнего обновления
    if user.last_updated:
        days_since = (today - user.last_updated).days
    else:
        days_since = MAX_DAYS_WITHOUT_UPDATE  # нет данных – считаем совсем неактуальным

    # 2. Показатель актуальности Ai
    Ai = max(0.0, 1.0 - days_since / MAX_DAYS_WITHOUT_UPDATE)

    # 3. Уровень загрузки Li: занятые часы за последние 7 дней / (рабочих дней * рабочих часов в день)
    end = today
    start = end - timedelta(days=7)
    total_work_hours = db.query(func.sum(WorkEntry.hours)).filter(
        WorkEntry.user_id == user.id,
        WorkEntry.date.between(start, end)
    ).scalar() or 0.0

    # Определяем рабочие часы в день по графику
    if user.work_start and user.work_end:
        # Преобразуем time в часы с минутами
        work_start_min = user.work_start.hour * 60 + user.work_start.minute
        work_end_min = user.work_end.hour * 60 + user.work_end.minute
        daily_work_minutes = max(0, work_end_min - work_start_min)
        daily_work_hours = daily_work_minutes / 60.0
    else:
        daily_work_hours = 8.0  # по умолчанию

    # Количество рабочих дней за неделю (учитываем work_days)
    if user.work_days:
        work_days_set = set(int(d) for d in user.work_days.split(","))
    else:
        work_days_set = {1,2,3,4,5}
    # подсчитываем дни от start до end, которые входят в рабочие
    current = start
    working_days = 0
    while current <= end:
        # weekday(): понедельник=0, воскресенье=6 -> преобразуем к 1..7
        iso_weekday = current.isoweekday()  # 1-7
        if iso_weekday in work_days_set:
            working_days += 1
        current += timedelta(days=1)

    max_possible_hours = working_days * daily_work_hours
    Li = round(total_work_hours / max_possible_hours, 3) if max_possible_hours > 0 else 0.0

    # 4. Доля встреч вне рабочего времени (Ci) за последние 30 дней
    month_start = today - timedelta(days=30)
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user.id,
        CalendarEvent.event_date >= month_start
    ).all()
    total_events = len(events)
    outside_events = 0
    for ev in events:
        # Проверяем, выходит ли событие за границы рабочего дня или за дни
        # Упрощённо: проверяем по времени, игнорируя дни (можно доработать)
        if user.work_start and user.work_end:
            start_min = ev.start_time.hour * 60 + ev.start_time.minute
            end_min = ev.end_time.hour * 60 + ev.end_time.minute
            work_start_min = user.work_start.hour * 60 + user.work_start.minute
            work_end_min = user.work_end.hour * 60 + user.work_end.minute
            if start_min < work_start_min or end_min > work_end_min:
                outside_events += 1
        # Также можно проверить день недели, но пока опустим
    Ci = round(outside_events / total_events, 3) if total_events > 0 else 0.0

    # 5. Интегральный риск Ri (упрощённые веса)
    w1, w2, w3 = 0.4, 0.3, 0.3  # без часового пояса и HR-расхождений
    Ri = round(w1*(1-Ai) + w2*Ci + w3*min(Li, 1.0), 3)

    return {
        "days_since_update": days_since,
        "Ai": round(Ai, 3),
        "Li": Li,
        "Ci": Ci,
        "Ri": Ri,
        "total_events": total_events,
        "outside_events": outside_events
    }