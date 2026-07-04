import os, json
from datetime import datetime
from data import load_data, save_data

MAX_LOGS = 500  # keep last 500 entries

def log_activity(action, entity_type, entity_id, entity_name, user_name, user_role, details=''):
    """Append one activity log entry."""
    try:
        d = load_data()
        logs = d.get('activity_log', [])
        logs.insert(0, {
            'time':        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'action':      action,          # 'Created' | 'Updated' | 'Deleted' | 'Login' | 'Stage Changed' etc.
            'entity_type': entity_type,     # 'Property' | 'Seller' | 'Buyer' | 'Employee' | 'Deal' | 'Viewing' | 'Task'
            'entity_id':   entity_id,
            'entity_name': entity_name,
            'user':        user_name,
            'role':        user_role,
            'details':     details,
        })
        d['activity_log'] = logs[:MAX_LOGS]
        save_data(d)
    except Exception:
        pass  # never crash the main request because of logging

def get_activity_log(limit=200):
    return load_data().get('activity_log', [])[:limit]
