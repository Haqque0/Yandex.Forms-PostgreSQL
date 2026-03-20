# Yandex.Forms-PostgreSQL
# Автоматизированный сбор данных из Yandex.Forms в PostgreSQL

## Состав проекта
* `db_parser.py` — сбор данных из Яндекс Форм и запись в базу данных PostgreSQL.
* `config_db.py` — файл конфигурации (токены и доступ к БД).

---

## 1. Подготовка базы данных (PostgreSQL)
Скрипт записывает данные напрямую в базу данных, запущенную в Docker-контейнере.

### Запуск контейнера
Для развертывания базы выполните команду:
```bash
docker run --name ctf-postgres \
  -e POSTGRES_PASSWORD=qwerty \
  -e POSTGRES_USER=ctf_user \
  -e POSTGRES_DB=ctf_db \
  -p 5432:5432 \
  -d postgres:15
```

---

## 2. API Яндекс Форм
Для доступа к API Яндекс Форм используется способ авторизации по протоколу OAuth 2.0.
Для работы скрипта нужны OAuth-токен, ID организации и ID формы.

### Подготовка
1. **OAuth-токен:** Создайте приложение на [oauth.yandex.ru](https://oauth.yandex.ru/). 
   - Тип: «Для доступа к API или отладки».
   - Выбрать доступ к данным: `forms:read` и `forms:write`.
   - После создания скопируйте у созданного приложения `ClientID`.
   - Cформируйте ссылку для запроса токена: `https://oauth.yandex.ru/authorize?response_type=token&client_id=ВАШ_ID`.
   - Войдите в аккаунт, от имени которого вы будете работать с API.
   - Скопируйте последовательность символов — это OAuth-токен.
2. **ID Организации:** берется в [профиле организации](https://center.yandex.cloud/).
3. **ID Формы:** берется из URL ссылки на форму. Пример: `https://forms.yandex.ru/cloud/admin/ID_ФОРМЫ/edit`.

## 3. Настройка конфига (config_db.py)
Переменные в файле:
- `OAUTH_TOKEN` — ваш OAuth-токен.
- `ORG_ID` — ID организации.
- `SURVEY_ID` — ID формы.
- `DB_CONFIG` — конфигурация базы данных (соответствует настройкам Docker-контейнера).
---

## 4. Настройка и использование
1. Необходимые библиотеки: `requests`, `psycopg2-binary`.
   ```bash
   pip3 install requests psycopg2-binary
   ```
2. Убедитесь, что Docker-контейнер с базой данных запущен.
    ```bash
   docker ps
   ```
3. Запустите основной скрипт:
   ```bash
   python3 db_parser.py
   ```

---

## 5. Проверка данных в базе

### Посмотреть список созданных команд:
```bash
docker exec -it ctf-postgres psql -U ctf_user -d ctf_db -c "SELECT * FROM teams;"
```

### Посмотреть список пользователей:
```bash
docker exec -it ctf-postgres psql -U ctf_user -d ctf_db -c "SELECT * FROM users;"
```
