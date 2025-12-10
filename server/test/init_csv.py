import os
import csv
import random
from datetime import datetime, timedelta
import json

# Генерация случайных данных
FIRST_NAMES = ["Alex", "Maria", "Ivan", "Anna", "Dmitry", "Elena", "Sergey", "Olga", "Nikita", "Tatiana"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
ROLES = ["admin", "manager", "member", "viewer"]
TASK_STATUSES = ["todo", "in_progress", "done"]
PRIORITIES = ["low", "medium", "high", "urgent"]
TAGS_POOL = ["backend", "frontend", "bug", "feature", "urgent", "ui", "api", "test", "docs", "security"]


def random_timestamp(start, end):
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def init_test_csv():
    os.makedirs("../data", exist_ok=True)

    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 10)

    print("Генерация пользователей (включая 2 статичных админа)...")
    users = []

    with open("../data/users.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "user_id", "telegram_user_id", "telegram_username",
            "full_name", "registration_timestamp", "last_login",
            "is_active", "role"
        ])

        # Статичные администраторы
        static_admins = [
            {
                "user_id": 1,
                "telegram_user_id": 111111111,
                "telegram_username": "admin_one",
                "full_name": "Admin One",
                "role": "admin"
            },
            {
                "user_id": 2,
                "telegram_user_id": 222222222,
                "telegram_username": "admin_two",
                "full_name": "Admin Two",
                "role": "admin"
            }
        ]

        now_str = end_date.strftime("%Y-%m-%d %H:%M:%S")
        for adm in static_admins:
            w.writerow([
                str(adm["user_id"]),
                str(adm["telegram_user_id"]),
                adm["telegram_username"],
                adm["full_name"],
                now_str,
                now_str,
                "True",
                "admin"
            ])
            users.append({
                "user_id": adm["user_id"],
                "telegram_user_id": adm["telegram_user_id"]
            })

        # Генерация остальных пользователей (998 шт, чтобы итого было 1000)
        for i in range(3, 1001):
            user_id = i
            telegram_user_id = random.randint(1_000_000_000, 9_999_999_999)
            # Убедимся, что ID не совпадает с админами
            while telegram_user_id in (111111111, 222222222):
                telegram_user_id = random.randint(1_000_000_000, 9_999_999_999)

            username = f"user_{telegram_user_id % 100000:05d}"
            full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            reg_time = random_timestamp(start_date, end_date)
            last_login = random_timestamp(reg_time, end_date)
            is_active = "True"
            role = random.choices(ROLES, weights=[1, 10, 70, 19])[0]

            w.writerow([
                str(user_id),
                str(telegram_user_id),
                username,
                full_name,
                reg_time.strftime("%Y-%m-%d %H:%M:%S"),
                last_login.strftime("%Y-%m-%d %H:%M:%S"),
                is_active,
                role
            ])
            users.append({
                "user_id": user_id,
                "telegram_user_id": telegram_user_id
            })

    print(f"✅ Создано {len(users)} пользователей (включая 2 админов)")

    # === Задачи ===
    print("Генерация задач (3–7 на пользователя)...")
    task_id = 1
    with open("../data/tasks.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "task_id", "title", "description", "status", "assignee_user_id",
            "creator_user_id", "created_at", "updated_at", "due_date",
            "completed_at", "priority", "tags"
        ])
        for user in users:
            num_tasks = random.randint(3, 7)
            for _ in range(num_tasks):
                created = random_timestamp(start_date, end_date)
                updated = random_timestamp(created, end_date)
                due = random_timestamp(updated, end_date + timedelta(days=30))
                status = random.choice(TASK_STATUSES)
                completed_at = ""
                if status == "done":
                    completed_at = updated.strftime("%Y-%m-%d %H:%M:%S")

                tags = random.sample(TAGS_POOL, k=random.randint(1, 3))
                priority = random.choice(PRIORITIES)
                assignee = user["user_id"] if random.random() > 0.2 else ""

                w.writerow([
                    str(task_id),
                    f"Task #{task_id}",
                    f"Auto-generated task for user {user['user_id']}",
                    status,
                    str(assignee),
                    str(user["user_id"]),
                    created.strftime("%Y-%m-%d %H:%M:%S"),
                    updated.strftime("%Y-%m-%d %H:%M:%S"),
                    due.strftime("%Y-%m-%d %H:%M:%S"),
                    completed_at,
                    priority,
                    json.dumps(tags, ensure_ascii=False)
                ])
                task_id += 1

    print(f"✅ Создано {task_id - 1} задач")

    # === Документы ===
    print("Генерация документов (1–3 на пользователя)...")
    doc_id = 1
    with open("../data/docs.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "doc_id", "name", "content", "creator_user_id", "created_at", "updated_at"
        ])
        for user in users:
            num_docs = random.randint(1, 3)
            for _ in range(num_docs):
                created = random_timestamp(start_date, end_date)
                updated = random_timestamp(created, end_date)
                w.writerow([
                    str(doc_id),
                    f"doc_{doc_id}.txt",
                    f"Content of document #{doc_id} by user {user['user_id']}",
                    str(user["user_id"]),
                    created.strftime("%Y-%m-%d %H:%M:%S"),
                    updated.strftime("%Y-%m-%d %H:%M:%S")
                ])
                doc_id += 1

    print(f"✅ Создано {doc_id - 1} документов")

    # === События ===
    print("Генерация календарных событий (1–2 на пользователя)...")
    event_id = 1
    with open("../data/events.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "event_id", "title", "start", "end", "creator_user_id", "created_at"
        ])
        for user in users:
            num_events = random.randint(1, 2)
            for _ in range(num_events):
                start = random_timestamp(start_date, end_date)
                end = start + timedelta(hours=random.randint(1, 4))
                created = random_timestamp(start_date, start)
                w.writerow([
                    str(event_id),
                    f"Meeting #{event_id}",
                    start.strftime("%Y-%m-%d %H:%M:%S"),
                    end.strftime("%Y-%m-%d %H:%M:%S"),
                    str(user["user_id"]),
                    created.strftime("%Y-%m-%d %H:%M:%S")
                ])
                event_id += 1

    print(f"✅ Создано {event_id - 1} событий")
    print("\n✅ Все CSV-файлы успешно сгенерированы в папке data/")


if __name__ == "__main__":
    init_test_csv()