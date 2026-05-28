# WorkTimeSync/routers/profile_router.py
"""
Просмотр и редактирование своего профиля рабочего времени.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, WorkFormat, GraphHistory
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates
from datetime import date, time
from services.notifications import create_notification

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def view_profile(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})

@router.post("/update")
def update_profile(request: Request,
                   work_start: str = Form(...),
                   work_end: str = Form(...),
                   work_days: str = Form("1,2,3,4,5"),
                   timezone: str = Form("Europe/Moscow"),
                   work_format: str = Form("office"),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_active_user)):
    # === Защита от пустых полей времени ===
    if not work_start or not work_start.strip():
        work_start = "09:00"
    if not work_end or not work_end.strip():
        work_end = "18:00"

    # === Парсинг времени: разрешён формат HH:MM или HH:MM:SS ===
    try:
        start_parts = work_start.strip().split(":")
        end_parts = work_end.strip().split(":")
        start_h, start_m = int(start_parts[0]), int(start_parts[1])
        end_h, end_m = int(end_parts[0]), int(end_parts[1])
    except (ValueError, IndexError):
        raise HTTPException(400, "Неверный формат времени. Используйте ЧЧ:ММ")

    # === Валидация формата работы ===
    try:
        new_work_format = WorkFormat(work_format)
    except ValueError:
        raise HTTPException(400, "Неверный формат работы")

    # === Сохраняем СТАРЫЕ значения в историю (до изменения) ===
    history_entry = GraphHistory(
        user_id=current_user.id,
        changed_at=date.today(),
        work_start=current_user.work_start,
        work_end=current_user.work_end,
        work_days=current_user.work_days,
        timezone=current_user.timezone,
        work_format=current_user.work_format.value if current_user.work_format else None
    )
    db.add(history_entry)
    db.commit()  # фиксируем, чтобы история точно сохранилась

    # === Присваиваем НОВЫЕ значения ===
    current_user.work_start = time(start_h, start_m)
    current_user.work_end = time(end_h, end_m)
    current_user.work_days = work_days
    current_user.timezone = timezone
    current_user.work_format = new_work_format
    current_user.last_updated = date.today()

    db.commit()

    # === Уведомление руководителю ===
    if current_user.team_id:
        # Ищем менеджера этой команды
        manager = db.query(User).filter(
            User.team_id == current_user.team_id,
            User.role == "manager"
        ).first()
        if manager:
            create_notification(
                db, manager,
                f"Сотрудник {current_user.full_name} обновил рабочий график",
                "/dashboard/manager"
            )

    return RedirectResponse(url="/profile", status_code=303)