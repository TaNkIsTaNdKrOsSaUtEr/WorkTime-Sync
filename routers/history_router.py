# WorkTimeSync/routers/history_router.py
"""
Просмотр истории изменений рабочего графика.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, GraphHistory, RoleEnum
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")
Roli_s_dopuskom = [RoleEnum.manager, RoleEnum.hr, RoleEnum.analyst]
@router.get("/", response_class=HTMLResponse)
def history_list(request: Request,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_active_user)):
    # Доступно руководителю и HR
    if current_user.role not in Roli_s_dopuskom:
        return RedirectResponse(url="/dashboard/")

    # Если руководитель — показываем историю только своей команды
    if current_user.role == RoleEnum.manager:
        team_member_ids = [m.id for m in db.query(User).filter(User.team_id == current_user.team_id).all()]
        history_entries = db.query(GraphHistory).filter(
            GraphHistory.user_id.in_(team_member_ids)
        ).order_by(GraphHistory.changed_at.desc()).all()
    else:
        # HR видит всю историю
        history_entries = db.query(GraphHistory).order_by(GraphHistory.changed_at.desc()).all()

    # Соберём имена пользователей
    user_ids = set()
    for h in history_entries:
        user_ids.add(h.user_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return templates.TemplateResponse("history.html", {
        "request": request,
        "history": history_entries,
        "users": users
    })
    