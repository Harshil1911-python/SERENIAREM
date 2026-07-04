import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_all_payments():
    return load_data().get('payments', [])

def save_payment(data):
    try:
        p = json.loads(data) if isinstance(data, str) else data
        p['id']         = str(uuid.uuid4())[:8].upper()
        p['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        p.setdefault('status', 'Pending')
        d = load_data()
        d.setdefault('payments', []).append(p)
        save_data(d)
        return p['id'], None
    except Exception as e:
        return None, str(e)

def update_payment(pay_id, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        payments = d.get('payments', [])
        idx = next((i for i, p in enumerate(payments) if p['id'] == pay_id), None)
        if idx is None: return False, 'Payment not found'
        for k, v in updates.items():
            if k not in {'id', 'created_at'}:
                payments[idx][k] = v
        payments[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d['payments'] = payments
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_payment(pay_id):
    try:
        d = load_data()
        orig = len(d.get('payments', []))
        d['payments'] = [p for p in d.get('payments', []) if p['id'] != pay_id]
        if len(d['payments']) == orig: return False, 'Payment not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def mark_payment_received(pay_id):
    try:
        d = load_data()
        for p in d.get('payments', []):
            if p['id'] == pay_id:
                p['status']      = 'Received'
                p['received_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(d)
                return True, None
        return False, 'Not found'
    except Exception as e:
        return False, str(e)
