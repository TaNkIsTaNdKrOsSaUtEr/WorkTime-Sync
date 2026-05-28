# WorkTimeSync/routers/roadmap_router.py
"""
Дорожная карта актуализации.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, RoleEnum
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates
from services.roadmap import generate_roadmap

router = APIRouter()
templates = Jinja2Templates(directory="templates")
Roli_s_dopuskom = [RoleEnum.manager, RoleEnum.hr, RoleEnum.analyst]

@router.get("/", response_class=HTMLResponse)
def roadmap(request: Request,
            db: Session = Depends(get_db),
            current_user: User = Depends(get_current_active_user)):
    # Доступно руководителю и HR
    if current_user.role not in Roli_s_dopuskom:
        return RedirectResponse(url="/dashboard/", status_code=303)

    team_id = current_user.team_id if current_user.role == RoleEnum.manager else None
    if team_id is None:
        # Для HR – можно показывать по всем командам? Пока упростим: редирект
        return RedirectResponse(url="/hr/")

    tasks = generate_roadmap(db, team_id)
    return templates.TemplateResponse("roadmap.html", {
        "request": request,
        "tasks": tasks
    })

    