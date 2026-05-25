# WorkTimeSync/routers/dashboard_router.py
"""
Дашборды по ролям: сотрудник, руководитель, HR.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
import plotly.express as px
import pandas as pd
from database import get_db
from models import User, WorkEntry, RoleEnum, Project
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates
from services.analytics import calculate_metrics

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/")
def dashboard_redirect(request: Request, current_user: User = Depends(get_current_active_user)):
    if current_user.role == RoleEnum.employee:
        return RedirectResponse(url="/dashboard/employee")
    elif current_user.role == RoleEnum.manager:
        return RedirectResponse(url="/dashboard/manager")
    elif current_user.role == RoleEnum.hr:
        return RedirectResponse(url="/hr/")  # сразу на HR-дашборд
    else:
        return RedirectResponse(url="/auth/login")

@router.get("/employee", response_class=HTMLResponse)
def employee_dashboard(request: Request, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_active_user)):
    entries = db.query(WorkEntry).filter(WorkEntry.user_id == current_user.id).order_by(WorkEntry.date.desc()).limit(30).all()
    start = date.today() - timedelta(days=30)
    data = db.query(WorkEntry.date, func.sum(WorkEntry.hours)).filter(
        WorkEntry.user_id == current_user.id,
        WorkEntry.date >= start
    ).group_by(WorkEntry.date).all()
    df = pd.DataFrame(data, columns=["date", "hours"])
    if not df.empty:
        fig = px.line(df, x="date", y="hours", title="Ваша загрузка за 30 дней")
        graph_html = fig.to_html(full_html=False)
    else:
        graph_html = "<p>Нет данных для графика</p>"
    projects = db.query(Project).all()
    return templates.TemplateResponse("employee_dashboard.html", {
        "request": request, "user": current_user, "entries": entries,
        "graph_html": graph_html, "projects": projects
    })

@router.get("/manager", response_class=HTMLResponse)
def manager_dashboard(request: Request, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    if current_user.role != RoleEnum.manager:
        return RedirectResponse(url="/dashboard/")
    team_members = db.query(User).filter(User.team_id == current_user.team_id).all()
    end = date.today()
    start = end - timedelta(days=7)
    stats = []
    for member in team_members:
        total = db.query(func.sum(WorkEntry.hours)).filter(
            WorkEntry.user_id == member.id,
            WorkEntry.date.between(start, end)
        ).scalar() or 0
        avg_daily = total / 7.0
        if avg_daily > 8: color = "red"
        elif avg_daily < 4: color = "yellow"
        else: color = "green"
        metrics = calculate_metrics(db, member)
        stats.append({
            "user_id": member.id,          # нужно для формы
            "name": member.full_name,
            "total_hours": total,
            "avg_daily": round(avg_daily,1),
            "color": color,
            "days_since_update": metrics["days_since_update"],
            "Ai": metrics["Ai"],
            "Ci": metrics["Ci"],
            "Li": metrics["Li"],
            "Ri": metrics["Ri"],
            "recommendations": generate_simple_recommendations(metrics)
        })
    fig = px.bar([{"Сотрудник": s["name"], "Сред. часов в день": s["avg_daily"]} for s in stats],
                 x="Сотрудник", y="Сред. часов в день", color="Сотрудник", title="Загрузка команды за неделю")
    graph_html = fig.to_html(full_html=False) if stats else "<p>Нет данных</p>"
    projects = db.query(Project).all()  # список проектов для формы

    # === ДОБАВЛЕНО: последние записи команды для удаления ===
    member_ids = [m.id for m in team_members]
    team_entries = db.query(WorkEntry).filter(
        WorkEntry.user_id.in_(member_ids)
    ).order_by(WorkEntry.date.desc()).limit(30).all()

    return templates.TemplateResponse("manager_dashboard.html", {
        "request": request, "user": current_user, "team_stats": stats, "graph_html": graph_html,
        "projects": projects, "team_entries": team_entries
    })

def generate_simple_recommendations(metrics: dict) -> list:
    recs = []
    if metrics["Ai"] < 0.5:
        recs.append("Подтвердите актуальность графика")
    if metrics["Ci"] > 0.3:
        recs.append("Много встреч вне рабочего времени – проверьте график")
    if metrics["Li"] > 0.8:
        recs.append("Сотрудник перегружен, ограничьте новые встречи")
    if metrics["days_since_update"] > 30:
        recs.append("График не обновлялся более 30 дней")
    return recs[:3]

@router.get("/team-availability", response_class=HTMLResponse)
def team_availability(request: Request, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    if current_user.role != RoleEnum.manager:
        return RedirectResponse(url="/dashboard/")
    team_members = db.query(User).filter(User.team_id == current_user.team_id).all()
    members_data = []
    for member in team_members:
        if member.work_start and member.work_end:
            start_min = member.work_start.hour * 60 + member.work_start.minute
            end_min = member.work_end.hour * 60 + member.work_end.minute
            start_h = round(start_min / 60, 2)
            end_h = round(end_min / 60, 2)
            members_data.append({
                "name": member.full_name,
                "start": start_h,
                "end": end_h,
                "days": member.work_days,
                "timezone": member.timezone,
                "format": member.work_format.value
            })
    return templates.TemplateResponse("team_availability.html", {
        "request": request,
        "team": members_data
    })

    