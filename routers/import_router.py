# WorkTimeSync/routers/import_router.py
"""
Импорт рабочих часов из CSV/JSON.
"""
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, WorkEntry, Project, RoleEnum
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates
import csv, json, io
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ALLOWED_EXTENSIONS = {"csv", "json"}

def process_csv(db: Session, text: str) -> (int, list):
    """Парсит CSV и возвращает (количество успешно добавленных, список ошибок)."""
    reader = csv.DictReader(io.StringIO(text))
    added = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):  # строки считаем с 2 (шапка = 1)
        try:
            # Ищем пользователя по username
            user = db.query(User).filter(User.username == row.get("username", "").strip()).first()
            if not user:
                errors.append(f"Строка {row_num}: пользователь '{row.get('username')}' не найден")
                continue
            # Ищем проект по имени (если project_name задано)
            project = None
            if row.get("project_name"):
                project = db.query(Project).filter(Project.name == row["project_name"].strip()).first()
                if not project:
                    errors.append(f"Строка {row_num}: проект '{row['project_name']}' не найден")
                    continue
            # Парсим часы и дату
            hours = float(row["hours"])
            work_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            entry = WorkEntry(user_id=user.id, project_id=project.id if project else None,
                              hours=hours, date=work_date)
            db.add(entry)
            added += 1
        except Exception as e:
            errors.append(f"Строка {row_num}: {e}")
    return added, errors

def process_json(db: Session, text: str) -> (int, list):
    """Парсит JSON-массив объектов и возвращает (добавлено, ошибки)."""
    try:
        data = json.loads(text)
        if not isinstance(data, list):
            return 0, ["JSON должен содержать массив объектов"]
    except Exception as e:
        return 0, [f"Ошибка чтения JSON: {e}"]

    added = 0
    errors = []
    for idx, obj in enumerate(data, start=1):
        try:
            user = db.query(User).filter(User.username == obj.get("username", "").strip()).first()
            if not user:
                errors.append(f"Объект {idx}: пользователь '{obj.get('username')}' не найден")
                continue
            project = None
            if obj.get("project_name"):
                project = db.query(Project).filter(Project.name == obj["project_name"].strip()).first()
                if not project:
                    errors.append(f"Объект {idx}: проект '{obj['project_name']}' не найден")
                    continue
            hours = float(obj["hours"])
            work_date = datetime.strptime(obj["date"], "%Y-%m-%d").date()
            entry = WorkEntry(user_id=user.id, project_id=project.id if project else None,
                              hours=hours, date=work_date)
            db.add(entry)
            added += 1
        except Exception as e:
            errors.append(f"Объект {idx}: {e}")
    return added, errors

@router.get("/", response_class=HTMLResponse)
def import_page(request: Request, current_user: User = Depends(get_current_active_user)):
    # Доступно руководителю и HR
    if current_user.role not in [RoleEnum.manager, RoleEnum.hr]:
        return RedirectResponse(url="/dashboard/", status_code=303)
    return templates.TemplateResponse("import.html", {"request": request})

@router.post("/", response_class=HTMLResponse)
async def upload_file(request: Request,
                      file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_active_user)):
    if current_user.role not in [RoleEnum.manager, RoleEnum.hr]:
        return RedirectResponse(url="/dashboard/", status_code=303)

    # Проверка расширения
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return templates.TemplateResponse("import.html", {
            "request": request,
            "error": f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
        })

    content = (await file.read()).decode("utf-8")
    added = 0
    errors = []

    if ext == "csv":
        added, errors = process_csv(db, content)
    elif ext == "json":
        added, errors = process_json(db, content)

    if added > 0:
        db.commit()

    return templates.TemplateResponse("import.html", {
        "request": request,
        "imported": added,
        "errors": errors
    })

    