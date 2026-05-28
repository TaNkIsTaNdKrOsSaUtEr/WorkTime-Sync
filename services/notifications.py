# WorkTimeSync/services/notifications.py
"""
Сервис для создания уведомлений.
"""
from sqlalchemy.orm import Session
from models import User, Notification
from datetime import date

def create_notification(db: Session, user: User, message: str, link: str = None):
    notif = Notification(user_id=user.id, message=message, created_at=date.today(), link=link)
    db.add(notif)
    db.commit()
    