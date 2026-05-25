# WorkTimeSync/routers/project_router.py
"""
Управление проектами (создание/просмотр) для руководителя.
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException  # инструменты FastAPI: маршрутизатор, зависимости, запрос, данные формы, исключения
from fastapi.responses import HTMLResponse, RedirectResponse  # типы ответов: HTML-страница и редирект
from sqlalchemy.orm import Session  # тип сессии БД
from database import get_db  # зависимость для получения сессии БД
from models import Project, User, RoleEnum  # ORM-модели проекта, пользователя и перечисление ролей
from auth import get_current_active_user  # зависимость: получение текущего пользователя
from fastapi.templating import Jinja2Templates  # шаблонизатор Jinja2

router = APIRouter()  # создаём экземпляр маршрутизатора
templates = Jinja2Templates(directory="templates")  # указываем папку с HTML-шаблонами

@router.get("/", response_class=HTMLResponse)  # GET-запрос на /projects/ – список проектов
def list_projects(request: Request, db: Session = Depends(get_db),  # объект запроса, сессия БД
                  current_user: User = Depends(get_current_active_user)):  # текущий авторизованный пользователь
    if current_user.role not in [RoleEnum.manager, RoleEnum.hr]:  # проверка: доступ только у руководителя и HR
        raise HTTPException(403, "Недостаточно прав")  # иначе ошибка 403
    projects = db.query(Project).all()  # получаем все проекты из БД
    return templates.TemplateResponse("projects.html", {  # рендерим шаблон списка проектов
        "request": request,  # объект запроса (нужен Jinja2)
        "projects": projects,  # список проектов
        "user": current_user          # текущий пользователь (для проверки роли внутри шаблона, например, показывать кнопку создания)
    })

@router.post("/create")  # POST-запрос на /projects/create – создание проекта
def create_project(request: Request, name: str = Form(...),  # объект запроса, название проекта (из формы, обязательное)
                   db: Session = Depends(get_db),  # сессия БД
                   current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    if current_user.role != RoleEnum.manager:  # проверка: только руководитель может создавать проекты
        raise HTTPException(403, "Только руководитель может создавать проекты")  # иначе ошибка 403
    project = Project(name=name, manager_id=current_user.id)  # создаём объект нового проекта, ответственный — текущий руководитель
    db.add(project)  # добавляем проект в сессию
    db.commit()  # сохраняем в БД
    return RedirectResponse(url="/projects/", status_code=303)  # редирект на список проектов (303 See Other)
    