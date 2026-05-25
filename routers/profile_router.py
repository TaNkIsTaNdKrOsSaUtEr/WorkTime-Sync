# WorkTimeSync/routers/profile_router.py
"""
Просмотр и редактирование своего профиля рабочего времени.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, WorkFormat
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates
from datetime import date, time

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
    try:
        start_h, start_m = map(int, work_start.split(':'))
        end_h, end_m = map(int, work_end.split(':'))
        current_user.work_start = time(start_h, start_m)
        current_user.work_end = time(end_h, end_m)
    except:
        raise HTTPException(400, "Неверный формат времени")

    try:
        current_user.work_format = WorkFormat(work_format)
    except ValueError:
        raise HTTPException(400, "Неверный формат работы")

    current_user.work_days = work_days
    current_user.timezone = timezone
    current_user.last_updated = date.today()

    db.commit()
    return RedirectResponse(url="/profile", status_code=303)
