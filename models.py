# WorkTimeSync/models.py
"""
Модели SQLAlchemy для всех сущностей.
"""
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum as SaEnum, Time, Boolean, func 
from sqlalchemy.orm import relationship
from database import Base
import enum
from sqlalchemy import func

class RoleEnum(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    hr = "hr"
    project_manager = "project_manager"   # проектный менеджер
    analyst = "analyst"                   # аналитик

class AbsenceType(str, enum.Enum):
    vacation = "vacation"
    sick = "sick"

class AbsenceStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class WorkFormat(str, enum.Enum):
    office = "office"
    remote = "remote"
    hybrid = "hybrid"

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    members = relationship("User", back_populates="team")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SaEnum(RoleEnum), default=RoleEnum.employee, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Новые поля для рабочего графика
    work_start = Column(Time, default=None)          # начало рабочего дня, например 09:00
    work_end = Column(Time, default=None)            # конец рабочего дня, например 18:00
    work_days = Column(String, default="1,2,3,4,5")  # дни недели через запятую (1=пн, 7=вс)
    timezone = Column(String, default="Europe/Moscow")  # часовой пояс
    work_format = Column(SaEnum(WorkFormat), default=WorkFormat.office)
    last_updated = Column(Date, default=None)        # дата последнего обновления графика

    team = relationship("Team", back_populates="members")
    work_entries = relationship("WorkEntry", back_populates="user")
    absence_requests = relationship("AbsenceRequest", back_populates="user")
    calendar_events = relationship("CalendarEvent", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    graph_history = relationship("GraphHistory", back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    manager = relationship("User", foreign_keys=[manager_id])

class WorkEntry(Base):
    __tablename__ = "work_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    hours = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    user = relationship("User", back_populates="work_entries")
    project = relationship("Project")

class AbsenceRequest(Base):
    __tablename__ = "absence_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    type = Column(SaEnum(AbsenceType), default=AbsenceType.vacation)
    status = Column(SaEnum(AbsenceStatus), default=AbsenceStatus.pending)
    user = relationship("User", back_populates="absence_requests")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    hours = Column(Float, nullable=False)
    suggested_date = Column(Date, nullable=True)
    created_at = Column(Date)

class CalendarEvent(Base):
    """Упрощённая модель встреч/задач из календаря."""
    __tablename__ = "calendar_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(Time, nullable=False)          # время начала
    end_time = Column(Time, nullable=False)            # время окончания
    event_date = Column(Date, nullable=False)          # дата события
    event_type = Column(String, default="meeting")     # тип: meeting, task, etc.
    user = relationship("User", back_populates="calendar_events")

class Notification(Base):
    """Уведомления для пользователей."""
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # кому предназначено
    message = Column(String, nullable=False)          # текст уведомления
    created_at = Column(Date, default=func.now())     # дата создания
    is_read = Column(Boolean, default=False)          # прочитано или нет
    link = Column(String, nullable=True)              # ссылка для перехода (например, /ml/recommendations)
    user = relationship("User", back_populates="notifications")

class GraphHistory(Base):
    """История изменений рабочего графика сотрудника."""
    __tablename__ = "graph_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(Date, default=func.now())         # дата изменения
    work_start = Column(Time, nullable=True)              # старые значения (после изменения)
    work_end = Column(Time, nullable=True)
    work_days = Column(String, nullable=True)
    timezone = Column(String, nullable=True)
    work_format = Column(String, nullable=True)
    user = relationship("User", back_populates="graph_history")
