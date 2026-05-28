# WorkTimeSync/services/roadmap.py
"""
Генератор дорожной карты актуализации рабочих графиков.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import User, RoleEnum
from services.analytics import calculate_metrics

def generate_roadmap(db: Session, team_id: int):
    """
    Возвращает список задач (dict) для каждого сотрудника команды,
    отсортированный по приоритету (чем выше риск Ri, тем раньше).
    """
    team_members = db.query(User).filter(User.team_id == team_id).all()
    tasks = []

    for member in team_members:
        metrics = calculate_metrics(db, member)
        actions = []
        if metrics["days_since_update"] > 30:
            actions.append({
                "action": "Подтвердить актуальность графика",
                "reason": f"Не обновлялся {metrics['days_since_update']} дней",
                "priority": "high" if metrics["days_since_update"] > 60 else "medium"
            })
        if metrics["Ci"] > 0.3:
            actions.append({
                "action": "Проверить конфликты встреч",
                "reason": f"Доля встреч вне графика: {metrics['Ci']:.0%}",
                "priority": "medium"
            })
        if metrics["Li"] > 0.8:
            actions.append({
                "action": "Снизить нагрузку",
                "reason": f"Загрузка {metrics['Li']:.0%}, возможен перегруз",
                "priority": "high"
            })
        elif metrics["Li"] < 0.3:
            actions.append({
                "action": "Увеличить загрузку или пересмотреть задачи",
                "reason": f"Низкая загрузка ({metrics['Li']:.0%})",
                "priority": "low"
            })
        if metrics["Ai"] < 0.5:
            actions.append({
                "action": "Обновить данные о рабочем графике",
                "reason": f"Актуальность {metrics['Ai']:.2f}",
                "priority": "high" if metrics["Ai"] < 0.3 else "medium"
            })
        if metrics["Ri"] > 0.6:
            actions.append({
                "action": "Провести аудит рабочего времени",
                "reason": f"Интегральный риск {metrics['Ri']:.2f}",
                "priority": "high"
            })

        # Если никаких действий не требуется, всё равно добавим запись "в норме"
        if not actions:
            actions.append({
                "action": "Всё в порядке",
                "reason": "Метрики в норме",
                "priority": "none"
            })

        # Добавляем общий приоритет по максимальному среди действий
        priorities = {"high": 3, "medium": 2, "low": 1, "none": 0}
        overall_priority = max(priorities.get(a["priority"], 0) for a in actions)

        tasks.append({
            "user_id": member.id,
            "full_name": member.full_name,
            "actions": actions,
            "overall_priority": overall_priority,
            "Ri": metrics["Ri"]
        })

    # Сортируем по убыванию приоритета и риска
    tasks.sort(key=lambda x: (-x["overall_priority"], -x["Ri"]))
    return tasks

    