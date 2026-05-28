# WorkTimeSync/routers/ml_router.py
"""
Маршруты для ML-балансировки загрузки.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from database import get_db
from models import User, WorkEntry, RoleEnum, Recommendation
from auth import get_current_active_user
from services.recommendation import generate_recommendations
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/balance")
def run_balancing(request: Request, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    """
    Запуск ML-балансировки. Генерирует рекомендации, сохраняет в БД
    и перенаправляет на страницу с результатами.
    """
    if current_user.role != RoleEnum.manager:
        raise HTTPException(403, "Только руководитель может запускать балансировку")
    recomms = generate_recommendations(db, current_user.team_id)
    return RedirectResponse(url="/ml/recommendations", status_code=303)

@router.get("/recommendations", response_class=HTMLResponse)
def view_recommendations(request: Request, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_active_user)):
    """
    Показывает список последних рекомендаций для команды текущего руководителя.
    """
    if current_user.role != RoleEnum.manager:
        raise HTTPException(403, "Недостаточно прав")

    team_member_ids = [m.id for m in db.query(User).filter(User.team_id == current_user.team_id).all()]
    recomms = db.query(Recommendation).filter(
        (Recommendation.from_user_id.in_(team_member_ids)) |
        (Recommendation.to_user_id.in_(team_member_ids))
    ).order_by(Recommendation.id.desc()).all()

    user_ids = set()
    for r in recomms:
        user_ids.add(r.from_user_id)
        user_ids.add(r.to_user_id)
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return templates.TemplateResponse("recommendations.html", {
        "request": request,
        "recommendations": recomms,
        "users": users
    })
    