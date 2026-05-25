# WorkTimeSync/services/recommendation.py
"""
Модуль интеллектуальной балансировки загрузки с использованием KMeans.
Перед генерацией новых рекомендаций удаляет старые для команды руководителя.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, WorkEntry, Recommendation
from datetime import date, timedelta
from sklearn.cluster import KMeans
import numpy as np

def generate_recommendations(db: Session, team_id: int):
    today = date.today()
    start = today - timedelta(days=7)  # анализ за последнюю неделю

    members = db.query(User).filter(User.team_id == team_id).all()
    if len(members) < 2:
        return []  # не с кем балансировать

    user_ids = [m.id for m in members]
    user_names = {m.id: m.full_name for m in members}

    # === Очистка старых рекомендаций для этой команды ===
    db.query(Recommendation).filter(
        (Recommendation.from_user_id.in_(user_ids)) |
        (Recommendation.to_user_id.in_(user_ids))
    ).delete(synchronize_session=False)
    db.flush()

    # Средняя дневная загрузка за неделю
    avg_loads = []
    for uid in user_ids:
        total = db.query(func.sum(WorkEntry.hours)).filter(
            WorkEntry.user_id == uid,
            WorkEntry.date >= start
        ).scalar() or 0.0
        avg_loads.append(total / 7.0)

    if all(load == 0.0 for load in avg_loads):
        return []

    # Кластеризация на 3 группы: перегруженные, норма, недозагруженные
    X = np.array(avg_loads).reshape(-1, 1)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    centers = kmeans.cluster_centers_.flatten()

    # Определяем, какой кластер перегружен, а какой недозагружен
    cluster_order = np.argsort(centers)   # индексы по возрастанию центров
    under_cluster = cluster_order[0]      # самый низкий центр
    over_cluster = cluster_order[-1]      # самый высокий центр

    overloaded = [user_ids[i] for i in range(len(user_ids)) if clusters[i] == over_cluster]
    underloaded = [user_ids[i] for i in range(len(user_ids)) if clusters[i] == under_cluster]

    recommended_pairs = []
    for from_uid in overloaded:
        from_avg = avg_loads[user_ids.index(from_uid)]
        median_center = centers[cluster_order[1]]  # центр «нормы»
        excess_hours = max(0, from_avg - median_center)
        hours_to_move = max(1.0, round(excess_hours, 1))

        for to_uid in underloaded[:2]:  # не более 2 рекомендаций на одного перегруженного
            rec = Recommendation(
                from_user_id=from_uid,
                to_user_id=to_uid,
                project_id=None,
                hours=hours_to_move,
                suggested_date=today + timedelta(days=1)
            )
            db.add(rec)
            recommended_pairs.append({
                "from_user": user_names[from_uid],
                "to_user": user_names[to_uid],
                "hours": hours_to_move
            })
            db.flush()  # чтобы не копить в памяти

    db.commit()
    return recommended_pairs

    