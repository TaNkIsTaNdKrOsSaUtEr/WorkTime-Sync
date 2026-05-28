# WorkTimeSync/routers/notifications_router.py
"""
Уведомления для пользователей.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, Notification
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def list_notifications(request: Request,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    # Показываем уведомления текущего пользователя, последние сверху
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.id.desc()).all()
    # Количество непрочитанных
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "notifications": notifs,
        "unread_count": unread_count
    })

@router.get("/{notif_id}/read")
def mark_read(notif_id: int,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_active_user)):
    notif = db.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.commit()
    # Редирект на страницу уведомлений или на ссылку, если есть
    if notif and notif.link:
        return RedirectResponse(url=notif.link, status_code=303)
    return RedirectResponse(url="/notifications", status_code=303)
    