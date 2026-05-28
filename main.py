# WorkTimeSync/main.py
"""
Точка входа FastAPI приложения. Подключает маршруты, монтирует статику и Jinja2.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import engine, Base
from routers import auth_router, user_router, project_router, work_entry_router, absence_router, dashboard_router, hr_router, ml_router, profile_router
from routers import chat_router
from routers import import_router
from routers import notifications_router
from routers import roadmap_router
from routers import history_router
from routers import profile_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WorkTime Sync", version="1.0.0",
              description="Система синхронизации рабочего времени с AI-рекомендациями")

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")
app.state.templates = templates

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(user_router.router, prefix="/users", tags=["users"])
app.include_router(project_router.router, prefix="/projects", tags=["projects"])
app.include_router(work_entry_router.router, prefix="/work", tags=["work"])
app.include_router(absence_router.router, prefix="/absences", tags=["absences"])
app.include_router(dashboard_router.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(hr_router.router, prefix="/hr", tags=["hr"])
app.include_router(ml_router.router, prefix="/ml", tags=["ml"])
app.include_router(profile_router.router, prefix="/profile", tags=["profile"])
app.include_router(chat_router.router, prefix="/chat", tags=["chat"])
app.include_router(import_router.router, prefix="/import", tags=["import"])
app.include_router(notifications_router.router, prefix="/notifications", tags=["notifications"])
app.include_router(roadmap_router.router, prefix="/roadmap", tags=["roadmap"])
app.include_router(history_router.router, prefix="/history", tags=["history"])
app.include_router(profile_router.router, prefix="/profile", tags=["profile"])

@app.get("/")
def root():
    return {"message": "WorkTime Sync API is running"}
