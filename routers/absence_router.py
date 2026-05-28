# WorkTimeSync/routers/absence_router.py
"""
Маршруты для работы с запросами на отсутствие (отпуск, больничный).
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException  # инструменты FastAPI: маршрутизатор, зависимости, запрос, формы, исключения
from fastapi.responses import RedirectResponse, HTMLResponse  # ответы: редирект и HTML-страница
from sqlalchemy.orm import Session  # тип сессии БД
from datetime import date  # тип для работы с датами
from database import get_db  # зависимость для получения сессии БД
from models import User, AbsenceRequest, AbsenceType, AbsenceStatus, RoleEnum  # ORM-модели и перечисления
from auth import get_current_active_user  # зависимость: получает текущего пользователя по токену
from fastapi.templating import Jinja2Templates  # шаблонизатор Jinja2
from sqlalchemy import select as sa_select  # импортируем select из SQLAlchemy (для современных подзапросов)

router = APIRouter()  # создаём экземпляр маршрутизатора
templates = Jinja2Templates(directory="templates")  # указываем папку с HTML-шаблонами

@router.get("/", response_class=HTMLResponse)  # GET-запрос на /absences/ возвращает HTML
def list_absences(request: Request, db: Session = Depends(get_db),  # параметры: объект запроса, сессия БД (автоматически внедряется)
                  current_user: User = Depends(get_current_active_user)):  # текущий авторизованный пользователь
    if current_user.role == RoleEnum.employee:  # если роль = сотрудник
        absences = db.query(AbsenceRequest).filter(  # запрашиваем заявки на отсутствие
            AbsenceRequest.user_id == current_user.id  # фильтруем по ID текущего сотрудника
        ).order_by(AbsenceRequest.date_from.desc()).all()  # сортируем по дате начала (сначала новые)
    elif current_user.role == RoleEnum.manager:  # если роль = руководитель
        # Современный способ: используем select() для IN
        member_ids = sa_select(User.id).where(User.team_id == current_user.team_id)  # получаем ID всех членов команды руководителя
        absences = db.query(AbsenceRequest).filter(  # запрашиваем заявки
            AbsenceRequest.user_id.in_(member_ids)  # фильтруем по списку ID членов команды
        ).order_by(AbsenceRequest.date_from.desc()).all()  # сортируем по дате (сначала новые)
    else:  # иначе (HR или другая роль)
        absences = db.query(AbsenceRequest).order_by(AbsenceRequest.date_from.desc()).all()  # получаем вообще все заявки

    user_ids = list(set(a.user_id for a in absences))  # собираем уникальные ID пользователей из полученных заявок
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}  # получаем словарь пользователей: id → объект User
    return templates.TemplateResponse("absences.html", {  # рендерим шаблон absences.html и возвращаем HTML
        "request": request,  # передаём объект запроса (нужен Jinja2)
        "absences": absences,  # список заявок
        "users": users,  # словарь пользователей для отображения имён
        "user": current_user  # текущий пользователь (для проверки роли внутри шаблона)
    })

@router.post("/create")  # POST-запрос на /absences/create – создание заявки
def create_absence(request: Request,  # объект запроса
                   date_from: date = Form(...),  # дата начала (из формы, обязательное поле)
                   date_to: date = Form(...),  # дата окончания (из формы, обязательное)
                   absence_type: str = Form(...),  # тип отсутствия (строка из формы, обязательное)
                   db: Session = Depends(get_db),  # сессия БД
                   current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    try:
        type_enum = AbsenceType(absence_type)  # пробуем преобразовать строку в Enum AbsenceType
    except ValueError:  # если тип не соответствует ни одному значению Enum
        raise HTTPException(400, "Некорректный тип отсутствия")  # возвращаем ошибку 400
    if date_to < date_from:  # проверка: дата окончания не может быть раньше даты начала
        raise HTTPException(400, "Дата окончания раньше даты начала")  # ошибка 400
    new_req = AbsenceRequest(  # создаём новый объект заявки
        user_id=current_user.id,  # ID подавшего заявку (текущий пользователь)
        date_from=date_from,  # начало
        date_to=date_to,  # конец
        type=type_enum,  # тип (Enum)
        status=AbsenceStatus.pending  # статус по умолчанию — на рассмотрении
    )
    db.add(new_req)  # добавляем заявку в сессию
    db.commit()  # сохраняем в БД
    return RedirectResponse(url="/absences/", status_code=303)  # редирект на список заявок (303 See Other)
    manager = db.query(User).filter(User.team_id == current_user.team_id, User.role == "manager").first()
    if manager:
        create_notification(db, manager, f"Сотрудник {current_user.full_name} подал заявку на {type_enum.value}", "/absences/")




@router.post("/{absence_id}/approve")  # POST-запрос на /absences/{id}/approve – утвердить заявку
def approve_absence(absence_id: int, db: Session = Depends(get_db),  # ID заявки из пути, сессия БД
                    current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    if current_user.role != RoleEnum.manager:  # проверяем, что текущий пользователь — руководитель
        raise HTTPException(403, "Только руководитель может утверждать заявки")  # иначе 403
    absence = db.get(AbsenceRequest, absence_id)  # получаем заявку по ID
    if not absence:  # если заявка не найдена
        raise HTTPException(404, "Заявка не найдена")  # 404
    employee = db.get(User, absence.user_id)  # находим сотрудника, создавшего заявку
    if employee.team_id != current_user.team_id:  # проверяем, что сотрудник из той же команды, что и руководитель
        raise HTTPException(403, "Сотрудник не из вашей команды")  # иначе 403
    absence.status = AbsenceStatus.approved  # меняем статус на "утверждено"
    db.commit()  # сохраняем изменения
    return RedirectResponse(url="/absences/", status_code=303)  # редирект на список заявок

@router.post("/{absence_id}/reject")  # POST-запрос на /absences/{id}/reject – отклонить заявку
def reject_absence(absence_id: int, db: Session = Depends(get_db),  # ID заявки, сессия БД
                   current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    if current_user.role != RoleEnum.manager:  # проверка роли (только руководитель)
        raise HTTPException(403, "Только руководитель может отклонять заявки")  # 403
    absence = db.get(AbsenceRequest, absence_id)  # ищем заявку
    if not absence:  # если нет
        raise HTTPException(404, "Заявка не найдена")  # 404
    employee = db.get(User, absence.user_id)  # автор заявки
    if employee.team_id != current_user.team_id:  # проверка, что сотрудник из команды руководителя
        raise HTTPException(403, "Сотрудник не из вашей команды")  # 403
    absence.status = AbsenceStatus.rejected  # статус → отклонено
    db.commit()  # сохраняем
    return RedirectResponse(url="/absences/", status_code=303)  # редирект на список заявок
    