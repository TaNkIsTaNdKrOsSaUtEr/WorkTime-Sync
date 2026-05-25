# WorkTimeSync/routers/ml_router.py
"""
Маршруты для ML-балансировки загрузки.
"""
from fastapi import APIRouter, Depends, Request, HTTPException  # инструменты FastAPI: маршрутизатор, зависимости, запрос, исключения
from fastapi.responses import HTMLResponse, RedirectResponse  # типы ответов: HTML и редирект
from sqlalchemy.orm import Session  # сессия БД
from datetime import date, timedelta  # работа с датами и интервалами (не используется напрямую, импортировано)
from database import get_db  # зависимость для получения сессии БД
from models import User, WorkEntry, RoleEnum, Recommendation  # ORM-модели и перечисление ролей
from auth import get_current_active_user  # зависимость: получение текущего пользователя
from services.recommendation import generate_recommendations  # ML-функция, выполняющая кластеризацию и создание рекомендаций
from fastapi.templating import Jinja2Templates  # шаблонизатор для рендера HTML

router = APIRouter()  # создаём экземпляр маршрутизатора
templates = Jinja2Templates(directory="templates")  # указываем папку с HTML-шаблонами

@router.post("/balance")  # POST-запрос на /ml/balance – запуск ML-балансировки
def run_balancing(request: Request, db: Session = Depends(get_db),  # объект запроса, сессия БД
                  current_user: User = Depends(get_current_active_user)):  # текущий авторизованный пользователь
    """
    Запуск ML-балансировки. Генерирует рекомендации, сохраняет в БД
    и перенаправляет на страницу с результатами.
    """
    if current_user.role != RoleEnum.manager:  # проверяем, что пользователь — руководитель
        raise HTTPException(403, "Только руководитель может запускать балансировку")  # иначе ошибка 403
    recomms = generate_recommendations(db, current_user.team_id)  # вызываем ML-функцию: передаём сессию и ID команды
    return RedirectResponse(url="/ml/recommendations", status_code=303)  # редирект на страницу с рекомендациями (303 See Other)

@router.get("/recommendations", response_class=HTMLResponse)  # GET-запрос на /ml/recommendations – просмотр рекомендаций
def view_recommendations(request: Request, db: Session = Depends(get_db),  # объект запроса, сессия БД
                         current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    """
    Показывает список последних рекомендаций для команды текущего руководителя.
    """
    if current_user.role != RoleEnum.manager:  # только для руководителя
        raise HTTPException(403, "Недостаточно прав")  # иначе 403

    team_member_ids = [m.id for m in db.query(User).filter(User.team_id == current_user.team_id).all()]  # получаем список ID всех членов команды руководителя
    recomms = db.query(Recommendation).filter(  # запрашиваем рекомендации
        (Recommendation.from_user_id.in_(team_member_ids)) |  # где отправитель из команды
        (Recommendation.to_user_id.in_(team_member_ids))      # или получатель из команды
    ).order_by(Recommendation.id.desc()).all()  # сортируем по ID (сначала новые)

    user_ids = set()  # множество для сбора всех ID пользователей, упомянутых в рекомендациях
    for r in recomms:  # перебираем все рекомендации
        user_ids.add(r.from_user_id)  # добавляем ID отправителя
        user_ids.add(r.to_user_id)    # добавляем ID получателя
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}  # получаем словарь {id: объект User} для отображения имён

    return templates.TemplateResponse("recommendations.html", {  # рендерим шаблон рекомендаций
        "request": request,  # объект запроса
        "recommendations": recomms,  # список рекомендаций
        "users": users  # словарь пользователей (id → объект)
    })

    