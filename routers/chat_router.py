# WorkTimeSync/routers/chat_router.py
"""
AI-ассистент с локальной ML-моделью понимания намерений.
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from database import get_db
from models import User, WorkEntry, RoleEnum, Recommendation
from auth import get_current_active_user
from services.analytics import calculate_metrics
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
import joblib
import re
from services.meeting_scheduler import find_common_slot

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Загружаем модель (один раз при старте приложения)
try:
    intent_model = joblib.load('intent_model.joblib')
except:
    intent_model = None

def extract_employee_name(message: str, team_members: list) -> User | None:
    """Пытается найти имя сотрудника в сообщении."""
    msg_lower = message.lower()
    for member in team_members:
        if member.full_name.lower() in msg_lower:
            return member
    return None

def generate_answer(db: Session, current_user: User, message: str) -> str:
    """Генерирует ответ с помощью ML-модели намерений."""
    # Если модель не загружена (файл отсутствует), используем простой fallback
    if intent_model is None:
        return "Модель ИИ не загружена. Выполните train_intent_model.py"

    # Предсказываем намерение
    intent = intent_model.predict([message])[0]

    team_members = db.query(User).filter(User.team_id == current_user.team_id).all()
    if not team_members:
        return "У вас нет команды."

    # Обработка намерений
    if intent == "team_availability":
        intervals = []
        for m in team_members:
            if m.work_start and m.work_end:
                start_min = m.work_start.hour * 60 + m.work_start.minute
                end_min = m.work_end.hour * 60 + m.work_end.minute
                intervals.append((start_min, end_min, m.full_name))
        if not intervals:
            return "Нет данных о рабочем графике сотрудников."
        common_start, common_end = intervals[0][0], intervals[0][1]
        for start, end, _ in intervals[1:]:
            common_start = max(common_start, start)
            common_end = min(common_end, end)
        if common_start >= common_end:
            return "Общего рабочего окна нет."
        start_h, start_m = divmod(common_start, 60)
        end_h, end_m = divmod(common_end, 60)
        return f"Общее рабочее окно команды: с {start_h:02d}:{start_m:02d} до {end_h:02d}:{end_m:02d}."
    if intent == "about":
        return (
            "Я AI-ассистент WorkTime Sync.\n"
            "Могу подсказать:\n"
            "- загрузку и перегруз сотрудников\n"
            "- общее рабочее окно команды\n"
            "- последние рекомендации по балансировке\n"
            "- метрики конкретного сотрудника\n"
            "Просто спросите!"
        )
    elif intent == "overload":
        end = date.today()
        start = end - timedelta(days=7)
        lines = []
        for member in team_members:
            total = db.query(func.sum(WorkEntry.hours)).filter(
                WorkEntry.user_id == member.id,
                WorkEntry.date.between(start, end)
            ).scalar() or 0
            avg = total / 7.0
            if avg > 8:
                lines.append(f"{member.full_name}: перегруз ({avg:.1f} ч/день)")
            elif avg < 4:
                lines.append(f"{member.full_name}: недозагруз ({avg:.1f} ч/день)")
        if not lines:
            return "Все сотрудники в норме."
        return "Текущая ситуация:\n" + "\n".join(lines)

    elif intent == "recommendations":
        team_member_ids = [m.id for m in team_members]
        recomms = db.query(Recommendation).filter(
            (Recommendation.from_user_id.in_(team_member_ids)) |
            (Recommendation.to_user_id.in_(team_member_ids))
        ).order_by(Recommendation.id.desc()).limit(5).all()
        if not recomms:
            return "Пока нет рекомендаций. Запустите балансировку (кнопка на дашборде)."
        user_ids = set()
        for r in recomms:
            user_ids.add(r.from_user_id)
            user_ids.add(r.to_user_id)
        users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
        lines = []
        for r in recomms:
            from_name = users[r.from_user_id].full_name if r.from_user_id in users else "??"
            to_name = users[r.to_user_id].full_name if r.to_user_id in users else "??"
            lines.append(f"Переместить {r.hours} ч от {from_name} к {to_name}")
        return "Последние рекомендации:\n" + "\n".join(lines)

    elif intent == "employee_info":
        employee = extract_employee_name(message, team_members)
        if not employee:
            return "Не удалось понять, о каком сотруднике речь. Уточните имя."
        metrics = calculate_metrics(db, employee)
        return (
            f"Сотрудник: {employee.full_name}\n"
            f"Актуальность графика: {metrics['Ai']:.2f}\n"
            f"Конфликты (доля вне графика): {metrics['Ci']:.2f}\n"
            f"Загрузка: {metrics['Li']:.2f}\n"
            f"Риск неактуальности: {metrics['Ri']:.2f}"
        )
    elif intent == "meeting_suggest":
        # Пробуем извлечь дату из сообщения (упрощённо)
        target_date = None
        msg_lower = message.lower()
        # Ищем завтра/сегодня/день недели
        today = date.today()
        if "завтра" in msg_lower:
            target_date = today + timedelta(days=1)
        elif "сегодня" in msg_lower:
            target_date = today
        elif "понедельник" in msg_lower:
            # находим ближайший понедельник
            days_ahead = 0 - today.weekday()  # понедельник = 0
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "вторник" in msg_lower:
            days_ahead = 1 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "среда" in msg_lower:
            days_ahead = 2 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "четверг" in msg_lower:
            days_ahead = 3 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "пятница" in msg_lower:
            days_ahead = 4 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "суббота" in msg_lower:
            days_ahead = 5 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        elif "воскресенье" in msg_lower:
            days_ahead = 6 - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
        else:
            # по умолчанию завтра
            target_date = today + timedelta(days=1)

        # Ищем общий слот
        slot = find_common_slot(db, team_members, target_date, min_duration_minutes=30)
        if slot:
            start_h, start_m = divmod(slot[0], 60)
            end_h, end_m = divmod(slot[1], 60)
            return f"Предлагаемое время встречи {target_date.strftime('%d.%m.%Y')}: с {start_h:02d}:{start_m:02d} до {end_h:02d}:{end_m:02d}."
        else:
            return f"На {target_date.strftime('%d.%m.%Y')} нет общего свободного окна продолжительностью 30 минут. Попробуйте другой день."
    
    # fallback
    return (
        "Я могу ответить на вопросы:\n"
        "- о загрузке и перегрузе\n"
        "- о доступности команды\n"
        "- о рекомендациях по балансировке\n"
        "- о конкретном сотруднике\n"
        "Попробуйте сформулировать запрос."
    )

@router.get("/", response_class=HTMLResponse)
def chat_page(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("chat.html", {"request": request, "answer": None})

@router.post("/", response_class=HTMLResponse)
def chat_message(request: Request,
                 message: str = Form(...),
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_active_user)):
    answer = generate_answer(db, current_user, message)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "message": message,
        "answer": answer
    })

    