# WorkTimeSync/services/meeting_scheduler.py
"""
Поиск оптимального времени для встречи команды.
"""
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from models import User, AbsenceRequest, CalendarEvent

def find_common_slot(db: Session, team_members: list, target_date: date, min_duration_minutes: int = 30):
    """
    Возвращает (start_minutes, end_minutes) первого общего свободного интервала
    на target_date, либо None.
    """
    # Собираем рабочие интервалы и занятость
    busy_intervals = []  # список (start_min, end_min) для каждого сотрудника
    for member in team_members:
        # Проверяем, работает ли сотрудник в этот день
        if member.work_days:
            try:
                work_days = [int(d) for d in member.work_days.split(',')]
            except:
                work_days = [1,2,3,4,5]
        else:
            work_days = [1,2,3,4,5]
        iso_weekday = target_date.isoweekday()  # 1-7
        if iso_weekday not in work_days:
            # Сотрудник не работает в этот день -> общее окно невозможно
            return None

        # Проверяем отсутствия
        absence = db.query(AbsenceRequest).filter(
            AbsenceRequest.user_id == member.id,
            AbsenceRequest.status == 'approved',  # только подтверждённые
            AbsenceRequest.date_from <= target_date,
            AbsenceRequest.date_to >= target_date
        ).first()
        if absence:
            # Сотрудник отсутствует весь день -> общее окно невозможно
            return None

        # Рабочие часы сотрудника
        if member.work_start and member.work_end:
            work_start = member.work_start.hour * 60 + member.work_start.minute
            work_end = member.work_end.hour * 60 + member.work_end.minute
        else:
            work_start = 9 * 60  # 09:00
            work_end = 18 * 60   # 18:00

        # Занятость из календаря (встречи/задачи) на эту дату
        events = db.query(CalendarEvent).filter(
            CalendarEvent.user_id == member.id,
            CalendarEvent.event_date == target_date
        ).all()
        # Превращаем рабочий день в список свободных интервалов, вычитая занятость
        free_intervals = [(work_start, work_end)]
        for ev in events:
            ev_start = ev.start_time.hour * 60 + ev.start_time.minute
            ev_end = ev.end_time.hour * 60 + ev.end_time.minute
            new_free = []
            for fs, fe in free_intervals:
                if ev_end <= fs or ev_start >= fe:
                    new_free.append((fs, fe))
                else:
                    if fs < ev_start:
                        new_free.append((fs, ev_start))
                    if ev_end < fe:
                        new_free.append((ev_end, fe))
            free_intervals = new_free
        # Добавляем свободные интервалы сотрудника в общий список занятости как "занятость" других не интересует,
        # но для поиска общего пересечения мы ищем пересечение свободных интервалов всех сотрудников.
        # Поэтому соберём список свободных интервалов для каждого сотрудника.
        # Пока алгоритм: для каждого сотрудника получаем множество свободных минут.
        if not hasattr(find_common_slot, 'member_free_sets'):
            find_common_slot.member_free_sets = []  # статическая переменная для хранения
        # Создадим множество свободных минут в пределах [work_start, work_end)
        free_minutes = set()
        for fs, fe in free_intervals:
            for minute in range(fs, fe):
                free_minutes.add(minute)
        find_common_slot.member_free_sets.append(free_minutes)

    # После сбора всех сотрудников находим пересечение свободных минут
    if not hasattr(find_common_slot, 'member_free_sets') or len(find_common_slot.member_free_sets) != len(team_members):
        return None

    common_free = find_common_slot.member_free_sets[0].copy()
    for s in find_common_slot.member_free_sets[1:]:
        common_free &= s

    # Ищем непрерывный интервал длиной >= min_duration_minutes
    sorted_minutes = sorted(common_free)
    if not sorted_minutes:
        return None

    start = sorted_minutes[0]
    prev = start
    for minute in sorted_minutes[1:]:
        if minute != prev + 1:
            # разрыв, проверим предыдущий интервал
            if prev - start + 1 >= min_duration_minutes:
                return (start, prev + 1)  # возвращаем start, end+1 (как время окончания)
            start = minute
        prev = minute
    # Проверим последний интервал
    if prev - start + 1 >= min_duration_minutes:
        return (start, prev + 1)

    return None

    