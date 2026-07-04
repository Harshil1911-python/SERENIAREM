import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_all_tasks():
    return load_data().get('tasks', [])

def save_task(data):
    try:
        task = json.loads(data) if isinstance(data, str) else data
        task['id']         = str(uuid.uuid4())[:8].upper()
        task['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task.setdefault('status', 'Pending')
        d = load_data()
        d.setdefault('tasks', []).append(task)
        save_data(d)
        return task['id'], None
    except Exception as e:
        return None, str(e)

def update_task(task_id, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        tasks = d.get('tasks', [])
        idx = next((i for i, t in enumerate(tasks) if t['id'] == task_id), None)
        if idx is None: return False, 'Task not found'
        for k, v in updates.items():
            if k not in {'id', 'created_at'}:
                tasks[idx][k] = v
        tasks[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d['tasks'] = tasks
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_task(task_id):
    try:
        d = load_data()
        orig = len(d.get('tasks', []))
        d['tasks'] = [t for t in d.get('tasks', []) if t['id'] != task_id]
        if len(d['tasks']) == orig: return False, 'Task not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def complete_task(task_id):
    try:
        d = load_data()
        for t in d.get('tasks', []):
            if t['id'] == task_id:
                t['status']       = 'Done'
                t['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(d)
                return True, None
        return False, 'Task not found'
    except Exception as e:
        return False, str(e)
