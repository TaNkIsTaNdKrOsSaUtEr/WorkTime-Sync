# WorkTimeSync/services/export.py
"""
Сервис для экспорта данных в Excel.
"""
from io import BytesIO
from openpyxl import Workbook
from sqlalchemy.orm import Session, joinedload
from models import WorkEntry

def generate_excel_report(db: Session) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "WorkTime Sync Report"
    ws.append(["Сотрудник", "Дата", "Часы", "Проект"])
    entries = db.query(WorkEntry).options(
        joinedload(WorkEntry.user),
        joinedload(WorkEntry.project)
    ).all()
    for entry in entries:
        ws.append([
            entry.user.full_name if entry.user else "Неизвестный",
            str(entry.date),
            entry.hours,
            entry.project.name if entry.project else "—"
        ])
    # Автоподбор ширины
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column_letter].width = max_length + 2
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
    