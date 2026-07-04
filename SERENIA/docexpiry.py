import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_all_expiries():
    return load_data().get('doc_expiries', [])

def save_expiry(data):
    try:
        e = json.loads(data) if isinstance(data, str) else data
        e['id']         = str(uuid.uuid4())[:8].upper()
        e['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d = load_data()
        d.setdefault('doc_expiries', []).append(e)
        save_data(d)
        return e['id'], None
    except Exception as ex:
        return None, str(ex)

def update_expiry(exp_id, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        exps = d.get('doc_expiries', [])
        idx  = next((i for i, e in enumerate(exps) if e['id'] == exp_id), None)
        if idx is None: return False, 'Not found'
        for k, v in updates.items():
            if k not in {'id','created_at'}:
                exps[idx][k] = v
        d['doc_expiries'] = exps
        save_data(d)
        return True, None
    except Exception as ex:
        return False, str(ex)

def delete_expiry(exp_id):
    try:
        d = load_data()
        orig = len(d.get('doc_expiries', []))
        d['doc_expiries'] = [e for e in d.get('doc_expiries', []) if e['id'] != exp_id]
        if len(d['doc_expiries']) == orig: return False, 'Not found'
        save_data(d)
        return True, None
    except Exception as ex:
        return False, str(ex)
