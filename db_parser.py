import requests
import psycopg2
import config_db
import json

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
        current_params = params if url == API_URL else None
        response = requests.get(url, headers=headers, params=current_params)

        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code} - {response.text}")
            break

        data = response.json()
        all_answers.extend(data.get("answers", []))

        next_data = data.get("next")
        if next_data and next_data.get("next_url"):
            raw_path = next_data.get("next_url")
            if "?" in raw_path:
                url = f"{API_URL}?{raw_path.split('?')[-1]}"
            else:
                url = None
        else:
            url = None
            
    return all_answers

def process_data(answers):
    answers.reverse()
    users = []

    # Вспомогательная функция для безопасного получения ответа по его номеру
    def get_val(d, index):
        # Проверяем, что индекс существует, элемент не пустой (не null) и это словарь
        if index < len(d) and d[index] and isinstance(d[index], dict):
            val = d[index].get("value")
            # Если ответ пришел списком, берем первый элемент
            if isinstance(val, list) and len(val) > 0:
                return val[0]
            return val
        return None

    for ans in answers:
        d = ans.get("data", [])
        
        # 1. Собираем данные первого участника по жестким индексам
        l_name = get_val(d, 0) or ""
        f_name = get_val(d, 1) or ""
        p_name = get_val(d, 2) or ""
        full_name = f"{l_name} {f_name} {p_name}".strip()
        
        email = get_val(d, 3)
        nickname = get_val(d, 4)

        # 2. Разбираемся с ВУЗом
        university = get_val(d, 5)
        if university == "Другое":
            university = get_val(d, 6) or "Не указан"

        # 3. Формат участия
        part_format = get_val(d, 7)

        if part_format == "Команда":
            team_name = get_val(d, 8) or "Без названия"
            users.append((full_name, email, nickname, university, team_name, "captain"))

            team_size_raw = get_val(d, 9)
            try:
                team_size = int(str(team_size_raw).split()[0])
            except (ValueError, TypeError):
                team_size = 1

            # 4. Парсим остальных участников по их индексам
            if team_size >= 2:
                users.append((get_val(d, 10), get_val(d, 11), get_val(d, 12), university, team_name, "member"))
            if team_size >= 3:
                users.append((get_val(d, 13), get_val(d, 14), get_val(d, 15), university, team_name, "member"))
            if team_size >= 4:
                users.append((get_val(d, 16), get_val(d, 17), get_val(d, 18), university, team_name, "member"))
        else:
            # Одиночное участие
            users.append((full_name, email, nickname, university, None, "individual"))

    return users

def save_to_db(users):
    conn = psycopg2.connect(**config_db.DB_CONFIG)
    cur = conn.cursor()

    # Создаем новую структуру таблицы
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            nickname VARCHAR(255),
            university VARCHAR(255),
            team_name VARCHAR(255),
            role VARCHAR(50)
        );
    """)

    # Полная очистка перед импортом
    cur.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")

    # Заполнение пользователей
    for u in users:
        # Защита от пустых записей
        if not u[1] and not u[2]: 
            continue
            
        try:
            cur.execute(
                """
                INSERT INTO users (full_name, email, nickname, university, team_name, role) 
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING;
                """,
                (u[0], u[1], u[2], u[3], u[4], u[5])
            )
        except Exception as e:
            print(f"Ошибка при добавлении {u[1]}: {e}")
            conn.rollback() # Откатываем транзакцию при ошибке (например, дубль email), чтобы продолжить цикл
            continue
            
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("Начинаю сбор данных...")
    data = fetch_all_answers()
    
    if data:
        # --- БЛОК ОТЛАДКИ ---
        # print("Служебная информация для настройки ключей:")
        # print(json.dumps(data[-1].get("data", []), indent=2, ensure_ascii=False))
        # --------------------

        users = process_data(data)
        save_to_db(users)
        print(f"Успех! Загружено пользователей: {len(users)}")
    else:
        print("Данные не получены. Проверьте токены в config_db.py")
