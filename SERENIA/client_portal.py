import os, json, uuid, secrets, hashlib
from datetime import datetime
from data import load_data, save_data

# ── Client Portal Sessions (separate from staff sessions) ──
_client_sessions = {}

def _hash_pw(pw, salt=None):
    if not salt: salt = secrets.token_hex(16)
    return salt + ':' + hashlib.sha256(f'{salt}{pw}'.encode()).hexdigest()

def _check_pw(pw, stored):
    try:
        salt, h = stored.split(':', 1)
        return hashlib.sha256(f'{salt}{pw}'.encode()).hexdigest() == h
    except: return False

# ── CRUD for client portal accounts ──

def get_all_portal_accounts():
    return load_data().get('client_portal_accounts', [])

def create_portal_account(person_type, person_id, username, password, created_by='admin'):
    """Create a portal login for a buyer or seller."""
    try:
        d  = load_data()
        accounts = d.get('client_portal_accounts', [])
        # Check username unique
        if any(a['username'].lower() == username.lower() for a in accounts):
            return False, 'Username already taken'
        account = {
            'id':          str(uuid.uuid4())[:8].upper(),
            'person_type': person_type,   # 'buyer' or 'seller'
            'person_id':   person_id,
            'username':    username,
            'password':    _hash_pw(password),
            'active':      True,
            'created_by':  created_by,
            'created_at':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login':  None,
        }
        d.setdefault('client_portal_accounts', []).append(account)
        save_data(d)
        return True, account['id']
    except Exception as e:
        return False, str(e)

def delete_portal_account(account_id):
    try:
        d = load_data()
        before = len(d.get('client_portal_accounts', []))
        d['client_portal_accounts'] = [a for a in d.get('client_portal_accounts', []) if a['id'] != account_id]
        if len(d['client_portal_accounts']) == before: return False, 'Not found'
        save_data(d)
        return True, None
    except Exception as e:
        return False, str(e)

def reset_portal_password(account_id, new_password):
    try:
        d = load_data()
        for a in d.get('client_portal_accounts', []):
            if a['id'] == account_id:
                a['password'] = _hash_pw(new_password)
                save_data(d)
                return True, None
        return False, 'Account not found'
    except Exception as e:
        return False, str(e)

# ── Client Portal Login ──

def client_login(username, password):
    d = load_data()
    for a in d.get('client_portal_accounts', []):
        if a['username'].lower() == username.lower() and a.get('active', True):
            if _check_pw(password, a['password']):
                token = secrets.token_hex(32)
                _client_sessions[token] = {
                    'account_id':  a['id'],
                    'person_type': a['person_type'],
                    'person_id':   a['person_id'],
                    'username':    a['username'],
                    'logged_in_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
                # Update last login
                a['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_data(d)
                return token, None
    return None, 'Invalid username or password'

def client_logout(token):
    _client_sessions.pop(token, None)

def get_client_session(token):
    return _client_sessions.get(token)

# ── Data access for client ──

def get_client_data(person_type, person_id):
    """Return everything a client needs to see in their portal."""
    d = load_data()

    if person_type == 'buyer':
        person = next((b for b in d.get('buyers', []) if b['id'] == person_id), None)
    else:
        person = next((s for s in d.get('sellers', []) if s['id'] == person_id), None)

    if not person: return None

    # Deals involving this person
    deals = [deal for deal in d.get('deals', []) if
             (person_type == 'buyer'  and deal.get('buyer_id')  == person_id) or
             (person_type == 'seller' and deal.get('seller_id') == person_id)]

    # Payments on those deals
    deal_ids = {deal['id'] for deal in deals}
    payments = [p for p in d.get('payments', []) if p.get('deal_id') in deal_ids]

    # Viewings
    viewings = []
    if person_type == 'buyer':
        viewings = [v for v in d.get('viewings', []) if v.get('buyer_id') == person_id]

    # Shortlisted properties
    shortlist_ids = person.get('shortlist', [])
    shortlisted   = [p for p in d.get('properties', []) if p['id'] in shortlist_ids]

    # Interested properties (for buyers)
    interested = []
    if person_type == 'buyer':
        int_ids  = person.get('interested_property_ids', [])
        interested = [p for p in d.get('properties', []) if p['id'] in int_ids]

    # Doc expiries for this person
    doc_expiries = [e for e in d.get('doc_expiries', [])
                    if e.get('person_type') == person_type and e.get('person_id') == person_id]

    # Enrich deals with property info
    for deal in deals:
        prop = next((p for p in d.get('properties', []) if p['id'] == deal.get('property_id')), None)
        deal['_property_title'] = prop['title'] if prop else deal.get('property_id', '—')
        deal['_payments'] = [p for p in payments if p.get('deal_id') == deal['id']]

    # Enrich viewings with property info
    for v in viewings:
        prop = next((p for p in d.get('properties', []) if p['id'] == v.get('property_id')), None)
        v['_property_title'] = prop['title'] if prop else '—'

    return {
        'person':      person,
        'person_type': person_type,
        'deals':       deals,
        'viewings':    viewings,
        'shortlisted': shortlisted,
        'interested':  interested,
        'doc_expiries': doc_expiries,
        'payments':    payments,
    }
