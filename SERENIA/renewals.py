import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_all_renewals():
    return load_data().get('renewals', [])

def save_renewal(data):
    try:
        r = json.loads(data) if isinstance(data, str) else data
        r['id']         = str(uuid.uuid4())[:8].upper()
        r['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        r.setdefault('status', 'Active')
        d = load_data()
        d.setdefault('renewals', []).append(r)
        save_data(d)
        return r['id'], None
    except Exception as e:
        return None, str(e)

def update_renewal(rid, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        renewals = d.get('renewals', [])
        idx = next((i for i,r in enumerate(renewals) if r['id']==rid), None)
        if idx is None: return False, 'Not found'
        for k,v in updates.items():
            if k not in {'id','created_at'}: renewals[idx][k] = v
        renewals[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d['renewals'] = renewals
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_renewal(rid):
    try:
        d = load_data()
        orig = len(d.get('renewals', []))
        d['renewals'] = [r for r in d.get('renewals', []) if r['id'] != rid]
        if len(d['renewals']) == orig: return False, 'Not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)
