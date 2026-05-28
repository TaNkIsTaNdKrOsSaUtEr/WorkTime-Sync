# WorkTimeSync/routers/hr_router.py
"""
HR-дашборд и экспорт отчёта.
"""
from fastapi import APIRouter, Depends, Request, HTTPException  # инструменты FastAPI: маршрутизатор, зависимости, запрос, исключения
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse  # типы ответов: HTML, потоковый (для Excel), редирект
from sqlalchemy.orm import Session  # тип сессии БД
from sqlalchemy import func  # функции агрегации (sum)
from datetime import date, timedelta  # работа с датами и интервалами (не используется в этом файле, но импортировано)
import plotly.express as px  # библиотека для построения графиков
import pandas as pd  # библиотека для работы с DataFrame
from database import get_db  # зависимость для получения сессии БД
from models import User, WorkEntry, RoleEnum  # ORM-модели и перечисление ролей
from auth import get_current_active_user  # зависимость: получение текущего пользователя
from fastapi.templating import Jinja2Templates  # шаблонизатор Jinja2
from services.export import generate_excel_report  # функция из сервисного слоя, генерирующая Excel
from services.pdf_export import generate_pdf_report

router = APIRouter()  # создаём экземпляр маршрутизатора
templates = Jinja2Templates(directory="templates")  # указываем папку с HTML-шаблонами

@router.get("/", response_class=HTMLResponse)  # GET-запрос на /hr/ – дашборд HR
def hr_dashboard(request: Request, db: Session = Depends(get_db),  # объект запроса, сессия БД
                 current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    if current_user.role != RoleEnum.hr:  # если роль не HR, доступ запрещён
        return RedirectResponse(url="/dashboard/")  # перенаправляем на общий дашборд (редирект)
    all_entries = db.query(WorkEntry.date, func.sum(WorkEntry.hours)).group_by(WorkEntry.date).all()  # получаем сумму часов по всем дням (все пользователи)
    df = pd.DataFrame(all_entries, columns=["date", "hours"])  # создаём DataFrame из результата запроса
    if not df.empty:  # если данные есть
        fig = px.line(df, x="date", y="hours", title="Общая загрузка компании")  # строим линейный график общей загрузки
        graph_html = fig.to_html(full_html=False)  # конвертируем график в HTML-код
    else:  # если данных нет
        graph_html = "<p>Нет данных</p>"  # заглушка
    return templates.TemplateResponse("hr_dashboard.html", {  # рендерим шаблон HR-дашборда
        "request": request,  # объект запроса
        "graph_html": graph_html  # HTML-код графика
    })

@router.get("/export")  # GET-запрос на /hr/export – экспорт отчёта в Excel
def export_excel(request: Request, db: Session = Depends(get_db),  # объект запроса, сессия БД
                 current_user: User = Depends(get_current_active_user)):  # текущий пользователь
    if current_user.role != RoleEnum.hr:  # проверка роли HR
        raise HTTPException(403, "Недостаточно прав")  # если не HR, выбрасываем ошибку 403
    stream = generate_excel_report(db)  # вызываем функцию генерации Excel, получаем BytesIO
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # отдаём файл через StreamingResponse
                             headers={"Content-Disposition": "attachment; filename=worktime_report.xlsx"})  # заголовок для скачивания файла с именем

@router.get("/export/pdf")
def export_pdf(request: Request, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_active_user)):
    if current_user.role not in [RoleEnum.hr, RoleEnum.manager]:
        raise HTTPException(403, "Недостаточно прав")
    # Если руководитель, берём его команду, иначе всю компанию
    team_id = current_user.team_id if current_user.role == RoleEnum.manager else None
    stream = generate_pdf_report(db, team_id)
    return StreamingResponse(stream, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=worktime_report.pdf"})
                             
                             