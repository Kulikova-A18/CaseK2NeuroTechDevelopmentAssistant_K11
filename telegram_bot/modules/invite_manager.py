import csv
import os
import secrets
import time
from .csv_storage import save_users

INVITES_CSV = 'invites.csv'

def init_invites_file():
    if not os.path.exists(INVITES_CSV):
        with open(INVITES_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'code', 'created_by_admin_username', 'created_at', 'used_by', 'used_at', 'is_active'
            ])
            writer.writeheader()

def generate_invite_code():
    return secrets.token_urlsafe(12)

def create_invite(admin_username):
    code = generate_invite_code()
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    with open(INVITES_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'code', 'created_by_admin_username', 'created_at', 'used_by', 'used_at', 'is_active'
        ])
        if f.tell() == 0:
            writer.writeheader()
        writer.writerow({
            'code': code,
            'created_by_admin_username': admin_username,
            'created_at': now,
            'used_by': '',
            'used_at': '',
            'is_active': 'True'
        })
    return code

def get_all_invites():
    invites = []
    if not os.path.exists(INVITES_CSV):
        return invites
    with open(INVITES_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            invites.append(row)
    return invites

def use_invite(code, telegram_user_id, telegram_username, full_name, users_by_id, users_by_username):
    if not os.path.exists(INVITES_CSV):
        return False, "Приглашения недоступны."

    updated_rows = []
    used = False
    success = False

    with open(INVITES_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['code'] == code and row['is_active'] == 'True' and not row['used_by']:
                # Регистрируем пользователя
                new_id = max([u['user_id'] for u in users_by_id.values()], default=0) + 1
                now = time.strftime('%Y-%m-%d %H:%M:%S')
                new_user = {
                    'user_id': new_id,
                    'telegram_user_id': int(telegram_user_id),
                    'telegram_username': telegram_username,
                    'full_name': full_name or telegram_username,
                    'registration_timestamp': now,
                    'last_login': now,
                    'is_active': True,
                    'role': 'member'
                }
                users_by_id[telegram_user_id] = new_user
                users_by_username[telegram_username.lower()] = new_user
                save_users(users_by_id)

                row['used_by'] = telegram_username
                row['used_at'] = now
                row['is_active'] = 'False'
                used = True
                success = True
            updated_rows.append(row)

    if used:
        with open(INVITES_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'code', 'created_by_admin_username', 'created_at', 'used_by', 'used_at', 'is_active'
            ])
            writer.writeheader()
            writer.writerows(updated_rows)

    if not success:
        return False, "Недействительное или уже использованное приглашение."

    return True, f"Вы успешно зарегистрированы как @{telegram_username}!"