# WorkTimeSync/routers/work_entry_router.py
"""
Маршруты для ввода и удаления рабочих часов.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from database import get_db
from models import WorkEntry, Project, User, RoleEnum
from auth import get_current_active_user

router = APIRouter()

@router.post("/add")
def add_work_entry(request: Request,
                   project_id: int = Form(...),
                   hours: float = Form(...),
                   work_date: date = Form(...),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_active_user)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(400, "Проект не найден")
    entry = WorkEntry(user_id=current_user.id, project_id=project_id, hours=hours, date=work_date)
    db.add(entry)
    db.commit()
    return RedirectResponse(url="/dashboard/employee", status_code=303)

@router.post("/add-for-user")
def add_work_entry_for_user(request: Request,
                            user_id: int = Form(...),
                            project_id: int = Form(...),
                            hours: float = Form(...),
                            work_date: date = Form(...),
                            db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_active_user)):
    if current_user.role not in [RoleEnum.manager, RoleEnum.hr]:
        raise HTTPException(403, "Недостаточно прав")
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(400, "Сотрудник не найден")
    if current_user.role == RoleEnum.manager and target_user.team_id != current_user.team_id:
        raise HTTPException(400, "Сотрудник не из вашей команды")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(400, "Проект не найден")
    entry = WorkEntry(user_id=user_id, project_id=project_id, hours=hours, date=work_date)
    db.add(entry)
    db.commit()
    return RedirectResponse(url="/dashboard/manager", status_code=303)

@router.post("/{entry_id}/delete")
def delete_work_entry(entry_id: int,
                      request: Request,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    """Удаляет запись. Автор или руководитель его команды."""
    entry = db.get(WorkEntry, entry_id)
    if not entry:
        raise HTTPException(404, "Запись не найдена")

    if entry.user_id != current_user.id:
        if current_user.role != RoleEnum.manager:
            raise HTTPException(403, "Недостаточно прав")
        author = db.get(User, entry.user_id)
        if not author or author.team_id != current_user.team_id:
            raise HTTPException(403, "Сотрудник не из вашей команды")

    db.delete(entry)
    db.commit()

    referer = request.headers.get("Referer", "/dashboard")
    return RedirectResponse(url=referer, status_code=303)

    