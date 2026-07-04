import os, json, uuid
from datetime import datetime
from data import load_data, save_data

SOURCES = ['Instagram','Facebook','Google Ads','Website','Referral','Walk-in','Cold Call','WhatsApp','Property Portal','Other']
STATUSES = ['New','Contacted','Qualified','Converted','Lost']

def get_all_leads():
    return load_data().get('leads', [])

def save_lead(data):
    try:
        lead = json.loads(data) if isinstance(data, str) else data
        lead['id']         = str(uuid.uuid4())[:8].upper()
        lead['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lead.setdefault('status', 'New')
        d = load_data()
        d.setdefault('leads', []).append(lead)
        save_data(d)
        return lead['id'], None
    except Exception as e:
        return None, str(e)

def update_lead(lead_id, data):
    try:
        updates = json.loads(data) if isinstance(data, str) else data
        d = load_data()
        leads = d.get('leads', [])
        idx = next((i for i, l in enumerate(leads) if l['id'] == lead_id), None)
        if idx is None: return False, 'Lead not found'
        for k, v in updates.items():
            if k not in {'id','created_at'}:
                leads[idx][k] = v
        leads[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        d['leads'] = leads
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_lead(lead_id):
    try:
        d = load_data()
        orig = len(d.get('leads', []))
        d['leads'] = [l for l in d.get('leads', []) if l['id'] != lead_id]
        if len(d['leads']) == orig: return False, 'Lead not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def convert_lead(lead_id, convert_to):
    """Mark lead as converted and return lead data for pre-filling buyer/seller form."""
    try:
        d = load_data()
        for l in d.get('leads', []):
            if l['id'] == lead_id:
                l['status']       = 'Converted'
                l['converted_to'] = convert_to
                l['converted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(d)
                return True, l
        return False, 'Lead not found'
    except Exception as e:
        return False, str(e)
