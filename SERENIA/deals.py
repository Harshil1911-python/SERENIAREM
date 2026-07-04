import os
import json
import uuid
from datetime import datetime
from data import load_data, save_data

def get_all_deals():
    return load_data().get('deals', [])

def save_deal(form_data_raw):
    try:
        deal = json.loads(form_data_raw)
        deal['id']         = str(uuid.uuid4())[:8].upper()
        deal['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        deal['updated_at'] = deal['created_at']
        deal.setdefault('stage', 'Inquiry')
        deal.setdefault('notes', '')
        data = load_data()
        data.setdefault('deals', []).append(deal)
        save_data(data)
        print(f"[SERENIA] Deal saved: {deal['id']} — {deal.get('title','')}")
        return deal['id'], None
    except Exception as e:
        return None, str(e)

def update_deal(deal_id, form_data_raw):
    try:
        updates = json.loads(form_data_raw)
        data    = load_data()
        deals   = data.get('deals', [])
        idx     = next((i for i, d in enumerate(deals) if d.get('id') == deal_id), None)
        if idx is None:
            return False, 'Deal not found'
        protected = {'id', 'created_at'}
        for k, v in updates.items():
            if k not in protected:
                deals[idx][k] = v
        deals[idx]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['deals'] = deals
        save_data(data)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_deal(deal_id):
    try:
        data  = load_data()
        orig  = len(data.get('deals', []))
        data['deals'] = [d for d in data.get('deals', []) if d.get('id') != deal_id]
        if len(data['deals']) == orig:
            return False, 'Deal not found'
        save_data(data)
        return True, None
    except Exception as e:
        return False, str(e)

def update_deal_stage(deal_id, stage):
    try:
        data  = load_data()
        for d in data.get('deals', []):
            if d.get('id') == deal_id:
                d['stage']      = stage
                d['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(data)
                return True, None
        return False, 'Deal not found'
    except Exception as e:
        return False, str(e)
