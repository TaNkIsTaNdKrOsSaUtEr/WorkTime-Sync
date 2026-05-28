# WorkTimeSync/train_intent_model.py
"""
Обучает модель классификации намерений для чат-бота.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

# Обучающие примеры: [фраза, намерение]
data = [
    # === Доступность команды ===
    ("когда вся команда доступна", "team_availability"),
    ("какое общее рабочее окно", "team_availability"),
    ("когда все работают", "team_availability"),
    ("покажи доступность команды", "team_availability"),
    ("окно для встречи", "team_availability"),
    ("когда можно собрать всех вместе", "team_availability"),
    ("удобное время для командного созвона", "team_availability"),
    ("есть ли у нас общее рабочее время", "team_availability"),

    # === Загрузка / перегруз ===
    ("кто перегружен", "overload"),
    ("у кого самая высокая загрузка", "overload"),
    ("покажи перегруз", "overload"),
    ("есть ли перегруженные сотрудники", "overload"),
    ("у кого недозагрузка", "overload"),
    ("покажи загрузку команды", "overload"),
    ("какая нагрузка у людей", "overload"),
    ("кто работает больше всех", "overload"),
    ("кто мало загружен", "overload"),

    # === Рекомендации ===
    ("что рекомендует система", "recommendations"),
    ("покажи рекомендации", "recommendations"),
    ("какие есть предложения по балансировке", "recommendations"),
    ("последние рекомендации", "recommendations"),
    ("балансировка", "recommendations"),
    ("какие советы даёт ИИ", "recommendations"),
    ("есть ли идеи по перераспределению задач", "recommendations"),

    # === Информация о сотруднике ===
    ("расскажи про ивана", "employee_info"),
    ("покажи метрики марии", "employee_info"),
    ("что с алексеем", "employee_info"),
    ("информация о сотруднике", "employee_info"),
    ("статистика по ольге", "employee_info"),
    ("как дела у дмитрия", "employee_info"),
    ("метрики павла", "employee_info"),
    ("что там у елены", "employee_info"),

    # === Общие вопросы / возможности ===
    ("кто ты", "about"),
    ("что ты умеешь", "about"),
    ("какие команды ты знаешь", "about"),
    ("помощь", "about"),
    ("что ты можешь", "about"),
    ("на что ты способен", "about"),
    ("справка", "about"),
    ("как ты работаешь", "about"),
    ("привет", "about"),
    ("здравствуй", "about"),
    ("как тебя зовут", "about"),

    # === Поиск времени для встречи ===
    ("найди время для встречи завтра", "meeting_suggest"),
    ("когда можно собраться в четверг", "meeting_suggest"),
    ("предложи окно для созвона", "meeting_suggest"),
    ("лучшее время для встречи", "meeting_suggest"),
    ("удобное время для командной встречи", "meeting_suggest"),
    ("когда пересекается свободное время", "meeting_suggest"),
    ("в какое время завтра все свободны", "meeting_suggest"),
    ("подбери слот для встречи", "meeting_suggest"),
]

texts = [item[0] for item in data]
labels = [item[1] for item in data]

# Создаём пайплайн: TF-IDF векторизатор + классификатор
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', LogisticRegression(random_state=42, max_iter=200))
])

pipeline.fit(texts, labels)

# Сохраняем модель
joblib.dump(pipeline, 'intent_model.joblib')
print("Модель намерений обучена и сохранена в intent_model.joblib")

