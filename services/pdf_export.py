# WorkTimeSync/services/pdf_export.py
"""
Сервис экспорта отчёта в PDF (устойчивый к отсутствию кириллических шрифтов).
"""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session
from models import User, WorkEntry
from sqlalchemy import func
from datetime import date, timedelta
import os

# === Регистрация Unicode-шрифта ===
FONT_NAME = 'Helvetica'  # fallback
FONT_AVAILABLE = False
font_paths = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Ubuntu/Debian
    "/usr/share/fonts/TTF/DejaVuSans.ttf",              # Arch/другие
    "static/DejaVuSans.ttf"
]
for path in font_paths:
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont('DejaVuSans', path))
        FONT_NAME = 'DejaVuSans'
        FONT_AVAILABLE = True
        break

styles = getSampleStyleSheet()
if FONT_AVAILABLE:
    for style in styles.byName.values():
        style.fontName = FONT_NAME

def generate_pdf_report(db: Session, team_id: int | None = None) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []

    # Заголовок
    title_style = styles['Title']
    title_style.fontName = FONT_NAME
    title_text = "WorkTime Sync – Отчёт о загрузке" if FONT_AVAILABLE else "WorkTime Sync – Load Report"
    title = Paragraph(title_text, title_style)
    story.append(title)
    story.append(Spacer(1, 12))

    # Данные за последние 7 дней
    end = date.today()
    start = end - timedelta(days=7)
    if team_id is None:
        team_members = db.query(User).all()
    else:
        team_members = db.query(User).filter(User.team_id == team_id).all()

    # Таблица
    headers = ["Сотрудник", "Часов за неделю", "Сред./день", "Статус"] if FONT_AVAILABLE else \
              ["Employee", "Hours/week", "Avg/day", "Status"]
    data = [headers]
    for member in team_members:
        total = db.query(func.sum(WorkEntry.hours)).filter(
            WorkEntry.user_id == member.id,
            WorkEntry.date.between(start, end)
        ).scalar() or 0
        avg = total / 7.0
        if FONT_AVAILABLE:
            if avg > 8:
                status = "Перегруз"
            elif avg < 4:
                status = "Недозагруз"
            else:
                status = "Норма"
        else:
            if avg > 8:
                status = "Overload"
            elif avg < 4:
                status = "Underload"
            else:
                status = "Normal"
        data.append([member.full_name, str(total), f"{avg:.1f}", status])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

    