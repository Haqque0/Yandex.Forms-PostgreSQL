import requests
import psycopg2
import config_db

# Базовый URL из конфига
API_URL = f"https://api.forms.yandex.net/v1/surveys/{config_db.SURVEY_ID}/answers"

def fetch_all_answers():
    headers = {
        "Authorization": f"OAuth {config_db.OAUTH_TOKEN}",
        "X-Org-ID": config_db.ORG_ID
    }
    params = {"page_size": 50}
    all_answers = []
    url = API_URL

    while url:
        # Параметры шлем только в первый запрос, в next_url они уже будут внутри строки
        current_params = params if url == API_URL else None
        response = requests.get(url, headers=headers, params=current_params)

        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code} - {response.text}")
            break

        data = response.json()
        all_answers.extend(data.get("answers", []))

        # Безопасная обработка следующей страницы
        next_data = data.get("next")
        if next_data and next_data.get("next_url"):
            raw_path = next_data.get("next_url")
            # Если в ссылке есть параметры (после ?), приклеиваем их к нашему v1 URL
            if "?" in raw_path:
                url = f"{API_URL}?{raw_path.split('?')[-1]}"
            else:
                url = None
        else:
            url = None
    return all_answers

def process_data(answers):
    # Разворачиваем, чтобы новые ответы были в конце
    answers.reverse()
    users, teams = [], []
    for ans in answers:
        d = ans.get("data", [])
        # Проверяем, что в ответе есть минимум 4 поля (Имя, Email, Пароль, Команда)
        if len(d) >= 4:
            user_info = [
                d[0].get("value"), # Name
                d[1].get("value"), # Email
                d[2].get("value"), # Password
                d[3].get("value"), # Team Name
                "user", "true", "false", "false"
            ]
            users.append(user_info)
            team_name = d[3].get("value")
            if team_name not in teams:
                teams.append(team_name)
    return users, teams

def save_to_db(users, teams):
    conn = psycopg2.connect(**config_db.DB_CONFIG)
    cur = conn.cursor()

    # Создание таблиц
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            email VARCHAR(255),
            password VARCHAR(255),
            hidden BOOLEAN DEFAULT false,
            banned BOOLEAN DEFAULT false
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            password VARCHAR(255),
            team_id VARCHAR(255),
            role VARCHAR(50),
            verified BOOLEAN DEFAULT true,
            hidden BOOLEAN DEFAULT false,
            banned BOOLEAN DEFAULT false
        );
    """)

    # Полная очистка перед импортом
    cur.execute("TRUNCATE TABLE users, teams RESTART IDENTITY CASCADE;")

    # Заполнение команд
    for i, t in enumerate(teams, 1):
        cur.execute(
            "INSERT INTO teams (name, email, password) VALUES (%s, %s, %s)",
            (t, f"team{i}@ctf.local", f"{t}_pass2026")
        )

    # Заполнение пользователей
    for u in users:
        cur.execute(
            "INSERT INTO users (name, email, password, team_id, role, verified, hidden, banned) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (u[0], u[1], u[2], u[3], u[4], u[5] == 'true', u[6] == 'true', u[7] == 'true')
        )

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("Начинаю сбор данных...")
    data = fetch_all_answers()
    if data:
        u, t = process_data(data)
        save_to_db(u, t)
        print(f"Успех! Загружено пользователей: {len(u)}, команд: {len(t)}")
    else:
        print("Данные не получены. Проверьте токены в config_db.py")
