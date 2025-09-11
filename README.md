# 🧼 Cleaning KIKI CRM & Website

**Cleaning KIKI** — это CRM-система и сайт-визитка клининговой компании,  
разработанные для автоматизации процессов: от приёма заказов до контроля работы клинеров.  

---

## 📖 Описание проекта

Проект объединяет:
- **CRM** для учёта заказов, клиентов, сотрудников и финансов
- **Сайт-визитку** для презентации компании клиентам
- **Telegram-бота** для удобного взаимодействия клинеров и менеджеров  

Cleaning CRM решает основные задачи клинингового бизнеса:  
✅ быстрый приём заказов  
✅ учёт и история клиентов  
✅ назначение сотрудников на уборку  
✅ контроль качества и рабочего времени  
✅ расчёт зарплат и аналитика  

---

## 🛠️ Требования

- **Docker**
- **Docker Compose**
- **Git** для клонирования проекта

---

## 🚀 Запуск проекта локально (development)

1. Клонировать репозиторий:

   ```sh
   git clone https://github.com/yourusername/cleaning-kiki.git
   cd cleaning-kiki/backend
   ```

2. Переименовать `.env-test` → `.env` и заполнить настройки:

   ```ini
   POSTGRES_DB=cleaning_db
   POSTGRES_USER=cleaning_user
   POSTGRES_PASSWORD=superpassword
   POSTGRES_HOST=db_kiki
   POSTGRES_PORT=5432

   DEBUG=True
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=127.0.0.1,localhost
   ```

3. Запустить контейнеры:

   ```sh
   sudo docker-compose -f docker/docker-compose.yml up -d --build
   ```

4. Миграции и сборка статики выполняются автоматически через `entrypoint.sh`.

5. (Опционально) загрузить демо-данные:

   ```sh
   sudo docker-compose exec web_raya python manage.py loaddata db.json
   ```

6. Проект будет доступен по адресу:

   👉 [http://127.0.0.1:8084](http://127.0.0.1:8084)

---

## 🌐 Запуск проекта на сервере (production)

1. Клонировать проект на сервер:

   ```sh
   git clone https://github.com/yourusername/cleaning-kiki.git
   cd cleaning-kiki/backend
   ```

2. Переименовать `.env-test` → `.env` и заполнить **продакшн-данные**.

3. Запустить продакшн-версию:

   ```sh
   sudo docker-compose -f docker/docker-compose-prod.yml up -d --build
   ```

4. Загрузить данные (если есть):

   ```sh
   sudo docker-compose -f docker/docker-compose-prod.yml exec web_kiki python manage.py loaddata db.json
   ```

5. Настроить SSL:

   **Остановить nginx:**
   ```sh
   sudo docker-compose -f docker/docker-compose-prod.yml stop nginx
   ```

   **Получить сертификат:**
   ```sh
   sudo certbot certonly --standalone -d crm.cleaningkiki.kg -d www.cleaningkiki.kg
   ```

   **Запустить nginx:**
   ```sh
   sudo docker-compose -f docker/docker-compose-prod.yml start nginx
   ```

---

## 📂 Структура репозитория

```
cleaning-kiki/
├── backend/                # Django-приложение (CRM + сайт)
│   ├── apps/               # Основные модули (клиенты, заказы, сотрудники)
│   ├── static/             # Статические файлы
│   ├── templates/          # HTML-шаблоны
│   └── manage.py
│
├── docker/                 # Docker-конфигурации
│   ├── docker-compose.yml
│   ├── docker-compose-prod.yml
│   └── entrypoint.sh
│
├── frontend/               # Фронтенд (шаблон сайта-визитки)
├── db.json                 # Демо-данные (опционально)
└── README.md
```

---

## 📦 Технологический стек

- **Backend**: Django (Python)  
- **Database**: PostgreSQL  
- **Cache/Broker**: Redis  
- **Frontend**: Bootstrap / HTML / CSS (адаптированный шаблон)  
- **Deployment**: Docker, Docker Compose  
- **Web-server**: Nginx (+ Certbot для HTTPS)  

---

## 🧩 Основные возможности Cleaning CRM

- Управление клиентами и заказами  
- Источники заказов (Instagram, сайт, Telegram, звонки)  
- Назначение клинеров и контроль выполнения  
- Учёт рабочего времени (через Telegram-бота)  
- Расчёт зарплат сотрудников  
- Финансовая аналитика (доходы, расходы, прибыль)  
- Дашборды для руководителя и менеджеров  

---

## 📞 Контакты

- 📱 Телефон: +996 XXX XX XX XX  
- 📧 Email: [cleaning.kiki@example.com](mailto:cleaning.kiki@example.com)  
- 📍 Адрес: г. Ош, Кыргызстан  

---
