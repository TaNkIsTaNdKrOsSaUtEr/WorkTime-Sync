# WorkTimeSync/routers/user_router.py
"""
Просмотр своего профиля.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_current_active_user
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/me", response_class=HTMLResponse)
def my_profile(request: Request, current_user: User = Depends(get_current_active_user)):
    return templates.TemplateResponse("employee_dashboard.html", {"request": request, "user": current_user})
