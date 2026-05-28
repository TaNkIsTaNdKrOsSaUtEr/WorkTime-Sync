# WorkTimeSync/tests/test_api.py
"""
Интеграционные тесты API.
"""
from datetime import date
from tests.conftest import get_token   # импортируем функцию

def test_login(client, seed_data):
    """Успешный вход через форму (проверяем, что возвращается редирект с установкой куки)."""
    response = client.post("/auth/login", data={"username": "manager", "password": "123"}, follow_redirects=False)
    # В тестовом клиенте без follow_redirects редирект отдаёт 303
    assert response.status_code == 303
    assert "access_token" in response.cookies

def test_token(client, seed_data):
    """Получение токена (данные пользователя есть благодаря seed_data)."""
    response = client.post("/auth/token", data={"username": "manager", "password": "123"})
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_manager_dashboard_access(client, seed_data):
    """Руководитель может открыть дашборд."""
    token = get_token(client, "manager")
    response = client.get("/dashboard/manager", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_employee_cannot_add_project(client, seed_data):
    """Сотрудник не может создать проект."""
    token = get_token(client, "employee")
    response = client.post("/projects/create", data={"name": "Forbidden"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_add_work_entry(client, seed_data):
    """Добавление рабочих часов."""
    token = get_token(client, "employee")
    response = client.post("/work/add", data={
        "project_id": seed_data["project"].id,
        "hours": 8,
        "work_date": str(date.today())
    }, headers={"Authorization": f"Bearer {token}"}, follow_redirects=False)
    assert response.status_code == 303

def test_ml_balance_access(client, seed_data):
    """Только руководитель может запустить балансировку."""
    token = get_token(client, "manager")
    response = client.post("/ml/balance", headers={"Authorization": f"Bearer {token}"}, follow_redirects=False)
    assert response.status_code == 303
    # Сотрудник не может
    token_emp = get_token(client, "employee")
    response_emp = client.post("/ml/balance", headers={"Authorization": f"Bearer {token_emp}"}, follow_redirects=False)
    assert response_emp.status_code == 403
    
def test_hr_export(client, seed_data):
    """HR может экспортировать Excel."""
    token = get_token(client, "hr")
    response = client.get("/hr/export", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

