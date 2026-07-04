import os
import json
import uuid
import hashlib
import secrets
from datetime import datetime
from data import load_data, save_data

# ── Permission levels ──
ROLES = {
    'admin':   3,   # full access
    'manager': 2,   # add/view, no delete, no user management
    'agent':   1,   # view + add only assigned data
}

def _hash_password(password, salt=None):
    """SHA-256 hash with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"

def _check_password(password, stored):
    """Verify password against stored salt:hash."""
    try:
        salt, hashed = stored.split(':', 1)
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
    except Exception:
        return False

def init_auth():
    """Create default admin user if no users exist."""
    data = load_data()
    if 'users' not in data:
        data['users'] = []

    if not data['users']:
        # Create default admin
        admin = {
            'id':         str(uuid.uuid4())[:8].upper(),
            'name':       'Administrator',
            'username':   'admin',
            'password':   _hash_password('admin123'),
            'role':       'admin',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        data['users'].append(admin)
        save_data(data)
        print("[SERENIA] Default admin created — username: admin  password: admin123")
        print("[SERENIA] ⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")

    if 'sessions' not in data:
        data['sessions'] = {}
        save_data(data)

def get_all_users():
    """Return all users (without passwords)."""
    data  = load_data()
    users = data.get('users', [])
    return [{k: v for k, v in u.items() if k != 'password'} for u in users]

def add_user(name, username, password, role):
    """Add a new user. Returns (user_id, None) or (None, error)."""
    try:
        if role not in ROLES:
            return None, 'Invalid role'
        if len(password) < 6:
            return None, 'Password must be at least 6 characters'

        data  = load_data()
        users = data.get('users', [])

        # Check username unique
        if any(u['username'].lower() == username.lower() for u in users):
            return None, f"Username '{username}' already exists"

        user = {
            'id':         str(uuid.uuid4())[:8].upper(),
            'name':       name,
            'username':   username.lower(),
            'password':   _hash_password(password),
            'role':       role,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        users.append(user)
        data['users'] = users
        save_data(data)
        print(f"[SERENIA] User added: {username} ({role})")
        return user['id'], None
    except Exception as e:
        return None, str(e)

def delete_user(user_id):
    """Delete a user by ID. Cannot delete last admin."""
    try:
        data  = load_data()
        users = data.get('users', [])
        user  = next((u for u in users if u['id'] == user_id), None)

        if not user:
            return False, 'User not found'
        if user['role'] == 'admin':
            admins = [u for u in users if u['role'] == 'admin']
            if len(admins) <= 1:
                return False, 'Cannot delete the last admin'

        data['users'] = [u for u in users if u['id'] != user_id]
        save_data(data)
        return True, None
    except Exception as e:
        return False, str(e)

def reset_password(user_id, new_password):
    """Reset a user's password."""
    try:
        if len(new_password) < 6:
            return False, 'Password must be at least 6 characters'
        data  = load_data()
        users = data.get('users', [])
        for u in users:
            if u['id'] == user_id:
                u['password'] = _hash_password(new_password)
                save_data(data)
                return True, None
        return False, 'User not found'
    except Exception as e:
        return False, str(e)

def login(username, password):
    """
    Verify credentials. Returns (session_token, user_info) or (None, error_msg).
    """
    try:
        data  = load_data()
        users = data.get('users', [])
        user  = next((u for u in users if u['username'].lower() == username.lower()), None)

        if not user:
            return None, 'Invalid username or password'
        if not _check_password(password, user['password']):
            return None, 'Invalid username or password'

        # Create session token
        token = secrets.token_hex(32)
        sessions = data.get('sessions', {})
        sessions[token] = {
            'user_id':    user['id'],
            'username':   user['username'],
            'name':       user['name'],
            'role':       user['role'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        data['sessions'] = sessions
        save_data(data)

        user_info = {
            'id':       user['id'],
            'name':     user['name'],
            'username': user['username'],
            'role':     user['role'],
        }
        print(f"[SERENIA] Login: {username} ({user['role']})")
        return token, user_info
    except Exception as e:
        return None, str(e)

def logout(token):
    """Invalidate a session token."""
    try:
        data     = load_data()
        sessions = data.get('sessions', {})
        if token in sessions:
            del sessions[token]
            data['sessions'] = sessions
            save_data(data)
        return True
    except Exception:
        return False

def get_session(token):
    """
    Return session info for a token, or None if invalid.
    """
    if not token:
        return None
    try:
        data     = load_data()
        sessions = data.get('sessions', {})
        return sessions.get(token)
    except Exception:
        return None

def require_role(session_info, min_role):
    """
    Check if session has at least the required role level.
    min_role: 'agent', 'manager', or 'admin'
    """
    if not session_info:
        return False
    user_level = ROLES.get(session_info.get('role', ''), 0)
    req_level  = ROLES.get(min_role, 99)
    return user_level >= req_level

def change_password(user_id, old_password, new_password):
    """Allow a user to change their own password."""
    try:
        if len(new_password) < 6:
            return False, 'New password must be at least 6 characters'
        data  = load_data()
        users = data.get('users', [])
        for u in users:
            if u['id'] == user_id:
                if not _check_password(old_password, u['password']):
                    return False, 'Current password is incorrect'
                u['password'] = _hash_password(new_password)
                save_data(data)
                return True, None
        return False, 'User not found'
    except Exception as e:
        return False, str(e)
