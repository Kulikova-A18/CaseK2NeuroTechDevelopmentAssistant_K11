def is_authorized(telegram_username, users_by_username):
    if not telegram_username:
        return None
    return users_by_username.get(telegram_username.lower())

def is_admin(user_record):
    return user_record and user_record.get('role') == 'admin'