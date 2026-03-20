import requests
import psycopg2

# Конфигурация Яндекса
OAUTH_TOKEN = "токен"
ORG_ID = "ID организации"
SURVEY_ID = "ID формы"
API_URL = f"https://api.forms.yandex.net/v1/surveys/{SURVEY_ID}/answers"

# Конфигурация локальной БД (соответствует настройкам Docker-контейнера)
DB_CONFIG = {
    "dbname": "ctf_db",
    "user": "ctf_user",
    "password": "qwerty",
    "host": "localhost",
    "port": "5432"
}

def fetch_all_answers():
    headers = {
        "Authorization": f"OAuth {OAUTH_TOKEN}",
        "X-Org-ID": ORG_ID
    }
    params = {"page_size": 50}
    all_answers = []
    url = API_URL

    while url:
        print(f"📡 Запрос к: {url}")
        current_params = params if url == API_URL else None
        response = requests.get(url, headers=headers, params=current_params)
        
        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            print(response.text)
            break
        
        data = response.json()
        all_answers.extend(data.get("answers", []))
        
        next_data = data.get("next")
        if next_data and next_data.get("next_url"):
            next_url = next_data.get("next_url")
            if not next_url.startswith('http'):
                next_url = f"https://api.forms.yandex.net{next_url}"
            if "/v3/" in next_url:
                next_url = next_url.replace("/v3/", "/v1/")
            url = next_url
        else:
            url = None
            
    return all_answers

def process_data(answers):
    answers.reverse() 
    users_data = []
    teams_list = []
    
    for ans in answers:
        d = ans.get("data", [])
        if len(d) >= 4:
            name = d[0].get("value")
            email = d[1].get("value")
            password = d[2].get("value")
            team_name = d[3].get("value")
            
            users_data.append([
                name, email, password, team_name, "user", "true", "false", "false"
            ])
            
            if team_name and team_name not in teams_list:
                teams_list.append(team_name)
    
    return users_data, teams_list

def init_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            email VARCHAR(255),
            password VARCHAR(255),
            hidden BOOLEAN DEFAULT false,
            banned BOOLEAN DEFAULT false
        )
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
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("🗄️ Структура базы данных проверена/создана.")

def save_to_db(users, teams):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Очищаем таблицы перед вставкой, чтобы при повторном запуске скрипта данные перезаписывались, а не дублировались
    cur.execute("TRUNCATE TABLE users, teams RESTART IDENTITY CASCADE;")

    for i, team_name in enumerate(teams, start=1):
        team_email = f"team{i}@ctf.local"
        team_pass = f"{team_name}_pass2026"
        cur.execute(
            "INSERT INTO teams (name, email, password, hidden, banned) VALUES (%s, %s, %s, %s, %s)",
            (team_name, team_email, team_pass, False, False)
        )

    for user in users:
        verified = user[5] == "true"
        hidden = user[6] == "true"
        banned = user[7] == "true"
        
        cur.execute(
            """INSERT INTO users (name, email, password, team_id, role, verified, hidden, banned) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user[0], user[1], user[2], user[3], user[4], verified, hidden, banned)
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ В базу данных записано: пользователей - {len(users)}, команд - {len(teams)}.")

if __name__ == "__main__":
    print("⚙️ Подготовка базы данных...")
    init_db()
    
    print("📥 Загрузка данных из Яндекс Форм...")
    raw_answers = fetch_all_answers()
    
    if raw_answers:
        users, teams = process_data(raw_answers)
        save_to_db(users, teams)
        print("🚀 Скрипт успешно отработал!")
    else:
        print("📭 Ответы не найдены.")
