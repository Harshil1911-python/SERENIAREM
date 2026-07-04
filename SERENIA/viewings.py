import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_all_viewings():
    return load_data().get('viewings', [])

def save_viewing(data):
    try:
        v = json.loads(data) if isinstance(data, str) else data
        v['id']         = str(uuid.uuid4())[:8].upper()
        v['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        v.setdefault('status', 'Scheduled')
        d = load_data()
        d.setdefault('viewings', []).append(v)
        save_data(d)
        return v['id'], None
    except Exception as e:
        return None, str(e)

def update_viewing(vid, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        viewings = d.get('viewings', [])
        idx = next((i for i, v in enumerate(viewings) if v['id'] == vid), None)
        if idx is None: return False, 'Viewing not found'
        for k, val in updates.items():
            if k not in {'id', 'created_at'}:
                viewings[idx][k] = val
        viewings[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d['viewings'] = viewings
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_viewing(vid):
    try:
        d = load_data()
        orig = len(d.get('viewings', []))
        d['viewings'] = [v for v in d.get('viewings', []) if v['id'] != vid]
        if len(d['viewings']) == orig: return False, 'Viewing not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def update_viewing_status(vid, status):
    try:
        d = load_data()
        for v in d.get('viewings', []):
            if v['id'] == vid:
                v['status'] = status
                save_data(d)
                return True, None
        return False, 'Viewing not found'
    except Exception as e:
        return False, str(e)
