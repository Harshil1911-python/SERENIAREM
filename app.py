import sys
import os
import threading
import re
import socket

# ── Load .env file if present ──
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Load saved API keys ──
try:
    import json as _j2
    _keys_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SERENIA', 'api_keys.json')
    if os.path.exists(_keys_path):
        with open(_keys_path) as _kf:
            _keys = _j2.load(_kf)
        if _keys.get('anthropic_api_key'):
            os.environ.setdefault('ANTHROPIC_API_KEY', _keys['anthropic_api_key'])
except: pass

SERENIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SERENIA')
FINANCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SERENIA', 'finance')
sys.path.insert(0, SERENIA_DIR)

# ── Launch finance app on port 5000 in background thread ──
def start_finance():
    try:
        sys.path.insert(0, FINANCE_DIR)
        os.chdir(FINANCE_DIR)
        import app as finance_app
        print("[SERENIA] Finance app starting on http://localhost:5000")
        finance_app.app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[SERENIA] Finance app failed to start: {e}")
    finally:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

finance_thread = threading.Thread(target=start_finance, daemon=True)
finance_thread.start()

from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context
import requests as req

from data       import init_data
from properties import init_folders,         get_all_properties,  save_property,   delete_property, \
                       update_property,       remove_property_file
from clients    import init_client_folders,  get_all_clients, \
                       get_all_sellers,       save_seller,     delete_seller,   update_seller, \
                       get_all_buyers,        save_buyer,      delete_buyer,    update_buyer
from employees  import init_emp_folders,     get_all_employees,   save_employee,   \
                       delete_employee,       update_employee_status, update_employee
from auth       import init_auth, login, logout, get_session, require_role, \
                       get_all_users, add_user, delete_user, reset_password, change_password
from messaging  import load_settings, save_settings, get_all_recipients, \
                       start_bulk_send, get_bulk_status
from deals      import get_all_deals, save_deal, update_deal, delete_deal, update_deal_stage
from tasks      import get_all_tasks, save_task, update_task, delete_task, complete_task
from viewings   import get_all_viewings, save_viewing, update_viewing, delete_viewing, update_viewing_status
from docexpiry  import get_all_expiries, save_expiry, update_expiry, delete_expiry
from activitylog import log_activity, get_activity_log
from notifications import get_notifications
from payments   import get_all_payments, save_payment, update_payment, \
                       delete_payment, mark_payment_received
from leads      import get_all_leads, save_lead, update_lead, delete_lead, convert_lead
from backup     import create_backup, restore_backup, get_backup_info
from branding   import load_branding, save_branding
import uuid

# ── Startup ──
init_data()
init_folders()
init_client_folders()
init_emp_folders()
init_auth()

app = Flask(__name__, static_folder=SERENIA_DIR)
app.secret_key = 'serenia-secret-2026'

FINANCE_BASE = 'http://127.0.0.1:5000'
PREFIX       = '/fin'

# ── Session helpers ──
def get_current_session():
    token = request.cookies.get('serenia_token')
    return get_session(token)

def session_required(min_role='agent'):
    sess = get_current_session()
    if not sess:
        return None, (jsonify({'success': False, 'error': 'Not logged in', 'redirect': '/'}), 401)
    if not require_role(sess, min_role):
        return None, (jsonify({'success': False, 'error': 'Access denied'}), 403)
    return sess, None

# ════════════════════════════════════════
#  FINANCE REVERSE PROXY
# ════════════════════════════════════════

def _rewrite_body(body):
    body = re.sub(r'(\.\./)+static/', '/fin/static/', body)

    def fix(m):
        attr, quote, p = m.group(1), m.group(2), m.group(3)
        if (p.startswith(PREFIX) or p.startswith('//') or p.startswith('http') or
                p.startswith('data:') or p.startswith('#') or p.startswith('mailto:')):
            return m.group(0)
        return f'{attr}{quote}{PREFIX}{p}'

    body = re.sub(r'((?:href|src|action)=)(["\'])(/[^"\']*)', fix, body)
    body = re.sub(r'''url\(\s*(['"]?)(/(?!fin)[^'"\)]*)\1\s*\)''',
                  lambda m: f"url('{PREFIX}{m.group(2)}')", body)
    body = re.sub(r'''(fetch|axios\.get|axios\.post|axios\.put|axios\.delete)\s*\(\s*(['"])(/(?!fin)[^'"]*)\2''',
                  lambda m: f"{m.group(1)}({m.group(2)}{PREFIX}{m.group(3)}{m.group(2)}", body)
    body = re.sub(r'''(window\.location(?:\.href)?\s*=\s*['"])(/(?!fin)[^'"]+)''',
                  lambda m: f"{m.group(1)}{PREFIX}{m.group(2)}", body)
    return body

def _proxy(path):
    target = f"{FINANCE_BASE}/{path}"
    if request.query_string:
        target += '?' + request.query_string.decode('utf-8')
    fwd_headers = {k: v for k, v in request.headers
                   if k.lower() not in ('host','content-length','transfer-encoding','connection')}
    try:
        resp = req.request(method=request.method, url=target, headers=fwd_headers,
                           data=request.get_data(), cookies=request.cookies,
                           allow_redirects=False, timeout=30)
    except req.exceptions.ConnectionError:
        return Response('<h2 style="font-family:sans-serif;color:#c00;padding:40px">Finance app is starting…<br>Wait a moment and reload.</h2>',
                        status=502, mimetype='text/html')

    skip = {'content-encoding','content-length','transfer-encoding','connection'}
    out_headers = []
    for k, v in resp.headers.items():
        if k.lower() in skip: continue
        if k.lower() == 'location':
            v = v.replace(FINANCE_BASE, '')
            if v.startswith('/') and not v.startswith(PREFIX): v = PREFIX + v
        if k.lower() == 'set-cookie':
            if 'path=/' in v.lower(): v = re.sub(r'[Pp]ath=/', f'Path={PREFIX}/', v, count=1)
        out_headers.append((k, v))

    ct = resp.headers.get('content-type', '')
    if any(x in ct for x in ('text/html','text/css','javascript')):
        body = resp.content.decode('utf-8', errors='replace')
        body = body.replace(FINANCE_BASE, '')
        body = _rewrite_body(body)
        return Response(body, status=resp.status_code, headers=out_headers)

    return Response(stream_with_context(resp.iter_content(chunk_size=8192)),
                    status=resp.status_code, headers=out_headers)

@app.route('/fin',           methods=['GET','POST','PUT','DELETE','PATCH'])
def fin_root():              return _proxy('')
@app.route('/fin/',          methods=['GET','POST','PUT','DELETE','PATCH'])
def fin_slash():             return _proxy('')
@app.route('/fin/<path:p>',  methods=['GET','POST','PUT','DELETE','PATCH'])
def fin_path(p):             return _proxy(p)

# ════════════════════════════════════════
#  AUTH ROUTES
# ════════════════════════════════════════

@app.route('/')
def root():
    return send_from_directory(SERENIA_DIR, 'login.html')

@app.route('/login', methods=['POST'])
def api_login():
    body     = request.get_json(silent=True) or {}
    username = body.get('username', '').strip()
    password = body.get('password', '')
    token, result = login(username, password)
    if not token:
        return jsonify({'success': False, 'error': result}), 401
    resp = jsonify({'success': True, 'role': result['role'], 'redirect': '/landpage'})
    resp.set_cookie('serenia_token', token, httponly=True, samesite='Lax', max_age=60*60*5)
    return resp

@app.route('/logout', methods=['POST'])
def api_logout():
    token = request.cookies.get('serenia_token')
    if token: logout(token)
    resp = jsonify({'success': True})
    resp.delete_cookie('serenia_token')
    return resp

@app.route('/get_users')
def api_get_users():
    sess, err = session_required('admin')
    if err: return err
    return jsonify(get_all_users())

@app.route('/add_user', methods=['POST'])
def api_add_user():
    sess, err = session_required('admin')
    if err: return err
    body = request.get_json(silent=True) or {}
    uid, error = add_user(body.get('name',''), body.get('username',''),
                          body.get('password',''), body.get('role','agent'))
    return jsonify({'success': True, 'id': uid}) if not error else (jsonify({'success': False, 'error': error}), 400)

@app.route('/delete_user/<uid>', methods=['DELETE'])
def api_delete_user(uid):
    sess, err = session_required('admin')
    if err: return err
    ok, error = delete_user(uid)
    return jsonify({'success': True}) if ok else (jsonify({'success': False, 'error': error}), 400)

@app.route('/reset_password/<uid>', methods=['POST'])
def api_reset_password(uid):
    sess, err = session_required('admin')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, error = reset_password(uid, body.get('password',''))
    return jsonify({'success': True}) if ok else (jsonify({'success': False, 'error': error}), 400)

@app.route('/me')
def api_me():
    sess = get_current_session()
    if not sess: return jsonify({'logged_in': False}), 401
    return jsonify({'logged_in': True, 'name': sess['name'],
                    'role': sess['role'], 'username': sess['username']})

# ════════════════════════════════════════
#  PROTECTED PAGE ROUTES
# ════════════════════════════════════════

def _protected_page(filename, min_role='agent'):
    sess = get_current_session()
    if not sess:
        return send_from_directory(SERENIA_DIR, 'login.html')
    if not require_role(sess, min_role):
        return "<h2 style='font-family:sans-serif;padding:40px;color:#c00'>Access Denied</h2>", 403
    return send_from_directory(SERENIA_DIR, filename)

@app.route('/landpage')
def landpage():     return _protected_page('landpage.html')
@app.route('/home')
def home():         return _protected_page('home.html')
@app.route('/admin')
def admin():        return _protected_page('admin.html', min_role='admin')

# Properties
@app.route('/prop')
def prop():         return _protected_page('prop.html')
@app.route('/list')
def list_prop():    return _protected_page('list.html')
@app.route('/list-india')
def list_india():   return _protected_page('list_india.html')
@app.route('/view')
def view():         return _protected_page('view.html')
@app.route('/view-uae')
def view_uae():     return _protected_page('view_uae.html')
@app.route('/view-india')
def view_india():   return _protected_page('view_india.html')
@app.route('/editprop')
def editprop():     return _protected_page('editprop.html')
@app.route('/propmap')
def propmap():      return _protected_page('propmap.html')

# Clients
@app.route('/clients')
def clients():      return _protected_page('clients.html')
@app.route('/seller')
def seller():       return _protected_page('seller.html')
@app.route('/buyer')
def buyer():        return _protected_page('buyer.html')
@app.route('/listseller')
def listseller():   return _protected_page('listseller.html')
@app.route('/viewseller')
def viewseller():   return _protected_page('viewseller.html')
@app.route('/listbuyer')
def listbuyer():    return _protected_page('listbuyer.html')
@app.route('/viewbuyer')
def viewbuyer():    return _protected_page('viewbuyer.html')
@app.route('/editseller')
def editseller():   return _protected_page('editseller.html')
@app.route('/editbuyer')
def editbuyer():    return _protected_page('editbuyer.html')

# Finance
@app.route('/finance')
def finance():      return _protected_page('finance.html')

# Employees
@app.route('/emp')
def emp():          return _protected_page('emp.html')
@app.route('/listemp')
def listemp():      return _protected_page('listemp.html')
@app.route('/viewemp')
def viewemp():      return _protected_page('viewemp.html')
@app.route('/editemp')
def editemp():      return _protected_page('editemp.html', min_role='manager')
@app.route('/messaging')
def messaging():    return _protected_page('messaging.html')
@app.route('/dashboard')
def dashboard():    return _protected_page('dashboard.html')
@app.route('/premium')
def premium():      return _protected_page('premium.html')
@app.route('/deals')
def deals():        return _protected_page('deals.html')
@app.route('/compare')
def compare():      return _protected_page('compare.html')
@app.route('/tasks')
def tasks():        return _protected_page('tasks.html')
@app.route('/viewings')
def viewings():     return _protected_page('viewings.html')
@app.route('/docexpiry')
def docexpiry():    return _protected_page('docexpiry.html')
@app.route('/activitylog')
def activitylog():  return _protected_page('activitylog.html', min_role='manager')
@app.route('/brochure')
def brochure():     return _protected_page('brochure.html')
@app.route('/payments')
def payments():     return _protected_page('payments.html')
@app.route('/leads')
def leads():        return _protected_page('leads.html')
@app.route('/commission')
def commission():   return _protected_page('commission.html')
@app.route('/settings')
def settings():     return _protected_page('settings.html')
@app.route('/invoice')
def invoice():      return _protected_page('invoice.html')
@app.route('/search')
def search():       return _protected_page('search.html')
@app.route('/leaderboard')
def leaderboard():  return _protected_page('leaderboard.html')
@app.route('/bulkstatus')
def bulkstatus():   return _protected_page('bulkstatus.html')
@app.route('/export')
def export():       return _protected_page('export.html')

# ════════════════════════════════════════
#  LEADS API
# ════════════════════════════════════════

@app.route('/get_leads')
def api_get_leads():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_leads())

@app.route('/save_lead', methods=['POST'])
def api_save_lead():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    lid, e = save_lead(body)
    return jsonify({'success':True,'id':lid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_lead/<lid>', methods=['POST'])
def api_update_lead(lid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_lead(lid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_lead/<lid>', methods=['DELETE'])
def api_delete_lead(lid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = delete_lead(lid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

@app.route('/convert_lead/<lid>', methods=['POST'])
def api_convert_lead(lid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, result = convert_lead(lid, body.get('convert_to','buyer'))
    return jsonify({'success':True,'lead':result}) if ok else (jsonify({'success':False,'error':result}),400)

# ════════════════════════════════════════
#  CHANGE PASSWORD
# ════════════════════════════════════════

@app.route('/change_password', methods=['POST'])
def api_change_password():
    sess = get_current_session()
    if not sess: return jsonify({'success':False,'error':'Not logged in'}),401
    body = request.get_json(silent=True) or {}
    ok, e = change_password(sess['user_id'], body.get('old_password',''), body.get('new_password',''))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),400)

# ════════════════════════════════════════
#  BRANDING API
# ════════════════════════════════════════

@app.route('/get_branding')
def api_get_branding():
    return jsonify(load_branding())

@app.route('/save_branding', methods=['POST'])
def api_save_branding():
    sess, err = session_required('admin')
    if err: return err
    import json as _json
    raw = request.form.get('data','{}')
    logo = request.files.get('logo')
    ok, e = save_branding(_json.loads(raw), logo)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

# ════════════════════════════════════════
#  BACKUP & RESTORE API
# ════════════════════════════════════════

@app.route('/backup_info')
def api_backup_info():
    sess, err = session_required('admin')
    if err: return err
    return jsonify(get_backup_info())

@app.route('/download_backup')
def api_download_backup():
    sess, err = session_required('admin')
    if err: return err
    from flask import send_file
    buf      = create_backup()
    filename = f"serenia_backup_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=filename)

@app.route('/restore_backup', methods=['POST'])
def api_restore_backup():
    sess, err = session_required('admin')
    if err: return err
    f = request.files.get('backup')
    if not f: return jsonify({'success':False,'error':'No file uploaded'}),400
    ok, e = restore_backup(f.read())
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),400)

# ════════════════════════════════════════
#  NOTIFICATIONS API
# ════════════════════════════════════════

@app.route('/get_notifications')
def api_get_notifications():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_notifications())

# ════════════════════════════════════════
#  PAYMENTS API
# ════════════════════════════════════════

@app.route('/get_payments')
def api_get_payments():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_payments())

@app.route('/save_payment', methods=['POST'])
def api_save_payment():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    pid, e = save_payment(body)
    return jsonify({'success':True,'id':pid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_payment/<pid>', methods=['POST'])
def api_update_payment(pid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_payment(pid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_payment/<pid>', methods=['DELETE'])
def api_delete_payment(pid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_payment(pid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

@app.route('/mark_payment_received/<pid>', methods=['POST'])
def api_mark_payment_received(pid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = mark_payment_received(pid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

# ════════════════════════════════════════
#  TASKS API
# ════════════════════════════════════════

@app.route('/get_tasks')
def api_get_tasks():
    sess, err = session_required('agent'); 
    if err: return err
    return jsonify(get_all_tasks())

@app.route('/save_task', methods=['POST'])
def api_save_task():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    tid, e = save_task(body)
    return jsonify({'success':True,'id':tid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_task/<tid>', methods=['POST'])
def api_update_task(tid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_task(tid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/complete_task/<tid>', methods=['POST'])
def api_complete_task(tid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = complete_task(tid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_task/<tid>', methods=['DELETE'])
def api_delete_task(tid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = delete_task(tid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

# ════════════════════════════════════════
#  VIEWINGS API
# ════════════════════════════════════════

@app.route('/get_viewings')
def api_get_viewings():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_viewings())

@app.route('/save_viewing', methods=['POST'])
def api_save_viewing():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    vid, e = save_viewing(body)
    log_activity('Created', 'Viewing', vid or '', body.get('property_id',''), sess['name'], sess['role'])
    return jsonify({'success':True,'id':vid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_viewing/<vid>', methods=['POST'])
def api_update_viewing(vid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_viewing(vid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/update_viewing_status/<vid>', methods=['POST'])
def api_update_viewing_status(vid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_viewing_status(vid, body.get('status',''))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),400)

@app.route('/delete_viewing/<vid>', methods=['DELETE'])
def api_delete_viewing(vid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = delete_viewing(vid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

# ════════════════════════════════════════
#  DOC EXPIRY API
# ════════════════════════════════════════

@app.route('/get_expiries')
def api_get_expiries():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_expiries())

@app.route('/save_expiry', methods=['POST'])
def api_save_expiry():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    eid, e = save_expiry(body)
    return jsonify({'success':True,'id':eid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_expiry/<eid>', methods=['POST'])
def api_update_expiry(eid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_expiry(eid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_expiry/<eid>', methods=['DELETE'])
def api_delete_expiry(eid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_expiry(eid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

# ════════════════════════════════════════
#  ACTIVITY LOG API
# ════════════════════════════════════════

@app.route('/get_activity_log')
def api_get_activity_log():
    sess, err = session_required('manager')
    if err: return err
    return jsonify(get_activity_log())

@app.route('/clear_activity_log', methods=['POST'])
def api_clear_activity_log():
    sess, err = session_required('admin')
    if err: return err
    try:
        from data import load_data, save_data
        d = load_data()
        d['activity_log'] = []
        save_data(d)
        return jsonify({'success':True})
    except Exception as ex:
        return jsonify({'success':False,'error':str(ex)}),500

# ════════════════════════════════════════
#  DEALS API
# ════════════════════════════════════════

@app.route('/get_deals')
def api_get_deals():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_deals())

@app.route('/save_deal', methods=['POST'])
def api_save_deal():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    import json as _json
    did, e = save_deal(_json.dumps(body))
    return jsonify({'success':True,'id':did}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_deal/<did>', methods=['POST'])
def api_update_deal(did):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    import json as _json
    ok, e = update_deal(did, _json.dumps(body))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_deal/<did>', methods=['DELETE'])
def api_delete_deal(did):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_deal(did)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

@app.route('/update_deal_stage/<did>', methods=['POST'])
def api_update_deal_stage(did):
    sess, err = session_required('agent')
    if err: return err
    body  = request.get_json(silent=True) or {}
    stage = body.get('stage','')
    ok, e = update_deal_stage(did, stage)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),400)

# ════════════════════════════════════════
#  MESSAGING API
# ════════════════════════════════════════

@app.route('/get_recipients')
def api_get_recipients():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_recipients())

@app.route('/get_msg_settings')
def api_get_msg_settings():
    sess, err = session_required('agent')
    if err: return err
    s = load_settings()
    # Never expose the app password to the frontend fully
    safe = {
        'gmail':       s.get('gmail', ''),
        'sender_name': s.get('sender_name', 'SERENIA'),
        'has_password': bool(s.get('app_password', '')),
    }
    return jsonify(safe)

@app.route('/save_msg_settings', methods=['POST'])
def api_save_msg_settings():
    sess, err = session_required('manager')
    if err: return err
    body = request.get_json(silent=True) or {}
    existing = load_settings()
    new_settings = {
        'gmail':        body.get('gmail', existing.get('gmail','')).strip(),
        'sender_name':  body.get('sender_name', existing.get('sender_name','SERENIA')).strip(),
        # Only update password if a new one was sent
        'app_password': body.get('app_password', '').strip() or existing.get('app_password',''),
    }
    ok, error = save_settings(new_settings)
    return jsonify({'success': True}) if ok else (jsonify({'success': False, 'error': error}), 500)

@app.route('/send_bulk', methods=['POST'])
def api_send_bulk():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}

    ids      = body.get('recipient_ids', [])
    subject  = body.get('subject', '').strip()
    template = body.get('body', '').strip()

    if not ids:      return jsonify({'success': False, 'error': 'No recipients selected'}), 400
    if not subject:  return jsonify({'success': False, 'error': 'Subject is required'}), 400
    if not template: return jsonify({'success': False, 'error': 'Message body is required'}), 400

    settings = load_settings()
    if not settings.get('gmail'):
        return jsonify({'success': False, 'error': 'Gmail not configured in settings'}), 400

    # Filter recipients to only selected ids
    all_recips   = get_all_recipients()
    selected     = [r for r in all_recips if r['id'] in ids]

    job_id = str(uuid.uuid4())[:8].upper()
    start_bulk_send(job_id, selected, subject, template, settings)

    return jsonify({'success': True, 'job_id': job_id})

@app.route('/bulk_status/<job_id>')
def api_bulk_status(job_id):
    sess, err = session_required('agent')
    if err: return err
    status = get_bulk_status(job_id)
    if not status:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(status)

# Catch-all for static assets
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(SERENIA_DIR, filename)

# ════════════════════════════════════════
#  PROPERTY API
# ════════════════════════════════════════

@app.route('/save_property', methods=['POST'])
def api_save_property():
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    pid, e = save_property(raw, request.files.getlist('photos'), request.files.getlist('videos'))
    return jsonify({'success':True,'id':pid}) if not e else (jsonify({'success':False,'error':e}), 500)

@app.route('/get_properties')
def api_get_properties():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_properties())

@app.route('/update_property/<pid>', methods=['POST'])
def api_update_property(pid):
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    ok, e = update_property(pid, raw, request.files.getlist('photos'), request.files.getlist('videos'))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 500)

@app.route('/update_property_availability/<pid>', methods=['POST'])
def api_update_availability(pid):
    sess, err = session_required('agent')
    if err: return err
    body   = request.get_json(silent=True) or {}
    status = body.get('availability','Available')
    import json as _j
    ok, e  = update_property(pid, _j.dumps({'availability': status}), [], [])
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/update_property_bulk', methods=['POST'])
def api_update_property_bulk():
    sess, err = session_required('agent')
    if err: return err
    body  = request.get_json(silent=True) or {}
    ids   = body.get('ids', [])
    field = body.get('field', '')
    value = body.get('value', '')
    if not ids or not field: return jsonify({'success':False,'error':'Missing ids or field'}),400
    import json as _j
    errs = []
    for pid in ids:
        ok, e = update_property(pid, _j.dumps({field: value}), [], [])
        if not ok: errs.append(e)
    return jsonify({'success':True,'updated':len(ids)-len(errs),'errors':errs})

@app.route('/get_brochure_token/<pid>')
def api_get_brochure_token(pid):
    import hashlib, time
    secret = 'SERENIA_BROCHURE_2024'
    token  = hashlib.sha256(f'{pid}{secret}'.encode()).hexdigest()[:16]
    return jsonify({'token': token, 'url': f'/brochure_public?id={pid}&token={token}'})

@app.route('/brochure_public')
def brochure_public():
    import hashlib
    pid      = request.args.get('id','')
    token    = request.args.get('token','')
    secret   = 'SERENIA_BROCHURE_2024'
    expected = hashlib.sha256(f'{pid}{secret}'.encode()).hexdigest()[:16]
    if token != expected:
        return '<h2 style="font-family:sans-serif;text-align:center;padding:60px;color:#dc2626">❌ Invalid or expired brochure link</h2>', 403
    return send_from_directory(SERENIA_DIR, 'brochure_public.html')

@app.route('/delete_property/<pid>', methods=['DELETE'])
def api_delete_property(pid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_property(pid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 404)

@app.route('/remove_property_file/<pid>', methods=['POST'])
def api_remove_property_file(pid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = remove_property_file(pid, body.get('filename',''), body.get('type','photo'))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 500)

# ════════════════════════════════════════
#  CLIENTS API
# ════════════════════════════════════════

@app.route('/get_clients')
def api_get_clients():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_clients())

@app.route('/get_sellers')
def api_get_sellers():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_sellers())

@app.route('/save_seller', methods=['POST'])
def api_save_seller():
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    sid, e = save_seller(raw, request.files.get('seller_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True,'id':sid}) if not e else (jsonify({'success':False,'error':e}), 500)

@app.route('/update_seller/<sid>', methods=['POST'])
def api_update_seller(sid):
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    ok, e = update_seller(sid, raw, request.files.get('seller_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 500)

@app.route('/delete_seller/<sid>', methods=['DELETE'])
def api_delete_seller(sid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_seller(sid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 404)

@app.route('/get_buyers')
def api_get_buyers():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_buyers())

@app.route('/save_buyer', methods=['POST'])
def api_save_buyer():
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    bid, e = save_buyer(raw, request.files.get('buyer_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True,'id':bid}) if not e else (jsonify({'success':False,'error':e}), 500)

@app.route('/update_buyer/<bid>', methods=['POST'])
def api_update_buyer(bid):
    sess, err = session_required('agent')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    ok, e = update_buyer(bid, raw, request.files.get('buyer_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 500)

@app.route('/delete_buyer/<bid>', methods=['DELETE'])
def api_delete_buyer(bid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_buyer(bid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 404)

# ════════════════════════════════════════
#  EMPLOYEE API
# ════════════════════════════════════════

@app.route('/get_employees')
def api_get_employees():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_employees())

@app.route('/save_employee', methods=['POST'])
def api_save_employee():
    sess, err = session_required('manager')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    eid, e = save_employee(raw, request.files.get('emp_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True,'id':eid}) if not e else (jsonify({'success':False,'error':e}), 500)

@app.route('/update_employee/<eid>', methods=['POST'])
def api_update_employee(eid):
    sess, err = session_required('manager')
    if err: return err
    raw = request.form.get('data')
    if not raw: return jsonify({'success':False,'error':'No data'}), 400
    ok, e = update_employee(eid, raw, request.files.get('emp_photo'), request.files.getlist('doc_photos'))
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 500)

@app.route('/delete_employee/<eid>', methods=['DELETE'])
def api_delete_employee(eid):
    sess, err = session_required('admin')
    if err: return err
    ok, e = delete_employee(eid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 404)

@app.route('/update_employee_status/<eid>', methods=['POST'])
def api_update_emp_status(eid):
    sess, err = session_required('manager')
    if err: return err
    status = request.json.get('status') if request.is_json else None
    if status not in ('Active','Inactive'):
        return jsonify({'success':False,'error':'Invalid status'}), 400
    ok, e = update_employee_status(eid, status)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}), 404)

from renewals     import get_all_renewals, save_renewal, update_renewal, delete_renewal
from client_portal import (client_login, client_logout, get_client_session,
                            get_all_portal_accounts, create_portal_account,
                            delete_portal_account, reset_portal_password, get_client_data)

# ════════════════════════════════════════
#  NEW PAGE ROUTES
# ════════════════════════════════════════

@app.route('/renewals')
def renewals_page():  return _protected_page('renewals.html')

@app.route('/portal_login')
def portal_login_page():
    # Public — no login needed
    return send_from_directory(SERENIA_DIR, 'portal_login.html')

@app.route('/portal')
def portal_page():
    tok  = request.cookies.get('serenia_client_token','')
    sess = get_client_session(tok)
    if not sess: return send_from_directory(SERENIA_DIR, 'portal_login.html')
    return send_from_directory(SERENIA_DIR, 'portal.html')

# ════════════════════════════════════════
#  CLIENT PORTAL API
# ════════════════════════════════════════

@app.route('/client_login', methods=['POST'])
def api_client_login():
    body = request.get_json(silent=True) or {}
    tok, err = client_login(body.get('username',''), body.get('password',''))
    if err:
        return jsonify({'success': False, 'error': err}), 401
    from flask import make_response
    resp = make_response(jsonify({'success': True}))
    resp.set_cookie('serenia_client_token', tok, httponly=True, max_age=60*60*8)
    return resp

@app.route('/client_logout', methods=['POST'])
def api_client_logout():
    tok = request.cookies.get('serenia_client_token','')
    client_logout(tok)
    from flask import make_response
    resp = make_response(jsonify({'success': True}))
    resp.delete_cookie('serenia_client_token')
    return resp

@app.route('/portal_data')
def api_portal_data():
    tok  = request.cookies.get('serenia_client_token','')
    sess = get_client_session(tok)
    if not sess: return jsonify({'error': 'Not logged in'}), 401
    data = get_client_data(sess['person_type'], sess['person_id'])
    if not data: return jsonify({'error': 'Account data not found'}), 404
    return jsonify(data)

@app.route('/get_portal_accounts')
def api_get_portal_accounts():
    sess, err = session_required('manager')
    if err: return err
    return jsonify(get_all_portal_accounts())

@app.route('/create_portal_account', methods=['POST'])
def api_create_portal_account():
    sess, err = session_required('manager')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, result = create_portal_account(
        body.get('person_type','buyer'),
        body.get('person_id',''),
        body.get('username',''),
        body.get('password',''),
        sess['name']
    )
    return jsonify({'success': True, 'id': result}) if ok else (jsonify({'success': False, 'error': result}), 400)

@app.route('/delete_portal_account/<aid>', methods=['DELETE'])
def api_delete_portal_account(aid):
    sess, err = session_required('manager')
    if err: return err
    ok, e = delete_portal_account(aid)
    return jsonify({'success': True}) if ok else (jsonify({'success': False, 'error': e}), 404)

@app.route('/reset_portal_password/<aid>', methods=['POST'])
def api_reset_portal_password(aid):
    sess, err = session_required('manager')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = reset_portal_password(aid, body.get('password',''))
    return jsonify({'success': True}) if ok else (jsonify({'success': False, 'error': e}), 400)

# ── Shortlist toggle (buyer) ──
@app.route('/toggle_shortlist', methods=['POST'])
def api_toggle_shortlist():
    sess, err = session_required('agent')
    if err: return err
    body      = request.get_json(silent=True) or {}
    buyer_id  = body.get('buyer_id','')
    prop_id   = body.get('prop_id','')
    if not buyer_id or not prop_id:
        return jsonify({'success': False, 'error': 'Missing buyer_id or prop_id'}), 400
    from data import load_data, save_data
    d = load_data()
    for b in d.get('buyers', []):
        if b['id'] == buyer_id:
            sl = b.setdefault('shortlist', [])
            if prop_id in sl: sl.remove(prop_id); action = 'removed'
            else:             sl.append(prop_id); action = 'added'
            save_data(d)
            return jsonify({'success': True, 'action': action, 'shortlist': sl})
    return jsonify({'success': False, 'error': 'Buyer not found'}), 404

# ── Duplicate property ──
@app.route('/duplicate_property/<pid>', methods=['POST'])
def api_duplicate_property(pid):
    sess, err = session_required('agent')
    if err: return err
    import json as _j, copy
    from data import load_data, save_data
    from datetime import datetime
    d     = load_data()
    orig  = next((p for p in d.get('properties',[]) if p['id']==pid), None)
    if not orig: return jsonify({'success':False,'error':'Property not found'}),404
    clone             = copy.deepcopy(orig)
    clone['id']       = str(uuid.uuid4())[:8].upper()
    clone['title']    = (orig.get('title','') or '') + ' (Copy)'
    clone['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    clone['updated_at'] = clone['created_at']
    clone['availability'] = 'Available'
    # Don't clone photos/videos — keep references but mark as shared
    d['properties'].append(clone)
    save_data(d)
    return jsonify({'success': True, 'id': clone['id'], 'title': clone['title']})

# ════════════════════════════════════════
#  RENEWALS API
# ════════════════════════════════════════

@app.route('/get_renewals')
def api_get_renewals():
    sess, err = session_required('agent')
    if err: return err
    return jsonify(get_all_renewals())

@app.route('/save_renewal', methods=['POST'])
def api_save_renewal():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    rid, e = save_renewal(body)
    return jsonify({'success':True,'id':rid}) if not e else (jsonify({'success':False,'error':e}),500)

@app.route('/update_renewal/<rid>', methods=['POST'])
def api_update_renewal(rid):
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, e = update_renewal(rid, body)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),500)

@app.route('/delete_renewal/<rid>', methods=['DELETE'])
def api_delete_renewal(rid):
    sess, err = session_required('agent')
    if err: return err
    ok, e = delete_renewal(rid)
    return jsonify({'success':True}) if ok else (jsonify({'success':False,'error':e}),404)

# ════════════════════════════════════════
#  AI FEATURES + CHAT ROUTES
# ════════════════════════════════════════

from ai_features  import (generate_property_description, score_lead,
                           estimate_property_price, generate_email_sequence)
from chat         import (get_conversations, get_or_create_conversation,
                          send_message, get_messages, get_client_conversation,
                          get_total_unread_for_agents)

# ── AI: Generate property description ──
@app.route('/ai/describe_property/<pid>', methods=['POST'])
def api_ai_describe(pid):
    sess, err = session_required('agent')
    if err: return err
    from data import load_data
    props = load_data().get('properties', [])
    prop  = next((p for p in props if p['id'] == pid), None)
    if not prop: return jsonify({'success': False, 'error': 'Not found'}), 404
    text, e = generate_property_description(prop)
    return jsonify({'success': True, 'description': text}) if not e else (jsonify({'success': False, 'error': e}), 500)

# ── AI: Score lead ──
@app.route('/ai/score_lead/<lid>', methods=['POST'])
def api_ai_score_lead(lid):
    sess, err = session_required('agent')
    if err: return err
    from leads import get_all_leads
    lead = next((l for l in get_all_leads() if l['id'] == lid), None)
    if not lead: return jsonify({'success': False, 'error': 'Not found'}), 404
    result = score_lead(lead)
    return jsonify({'success': True, **result})

# ── AI: Score all leads ──
@app.route('/ai/score_all_leads', methods=['POST'])
def api_ai_score_all():
    sess, err = session_required('agent')
    if err: return err
    from leads import get_all_leads
    leads  = get_all_leads()
    scores = {}
    for l in leads:
        scores[l['id']] = score_lead(l)
    return jsonify({'success': True, 'scores': scores})

# ── AI: Price estimator ──
@app.route('/ai/estimate_price', methods=['POST'])
def api_ai_estimate():
    sess, err = session_required('agent')
    if err: return err
    body  = request.get_json(silent=True) or {}
    from data import load_data
    props = load_data().get('properties', [])
    result, e = estimate_property_price(
        body.get('property_type','Apartment'),
        body.get('bedrooms',''),
        body.get('area_sqft',''),
        body.get('city',''),
        body.get('region','UAE'),
        body.get('category','For Sale'),
        props
    )
    return jsonify({'success': True, 'estimate': result}) if not e else (jsonify({'success': False, 'error': e}), 500)

# ── AI: Email sequence ──
@app.route('/ai/email_sequence/<lid>', methods=['POST'])
def api_ai_email_seq(lid):
    sess, err = session_required('agent')
    if err: return err
    from leads import get_all_leads
    from branding import load_branding
    lead = next((l for l in get_all_leads() if l['id'] == lid), None)
    if not lead: return jsonify({'success': False, 'error': 'Not found'}), 404
    b = load_branding()
    seq, e = generate_email_sequence(
        lead.get('name',''), lead.get('intent',''), lead.get('budget',''),
        lead.get('currency','AED'), lead.get('prop_type',''), lead.get('location',''),
        b.get('company_name','SERENIA')
    )
    return jsonify({'success': True, 'sequence': seq}) if not e else (jsonify({'success': False, 'error': e}), 500)

# ════════════════════════════════════════
#  CHAT API
# ════════════════════════════════════════

@app.route('/chat/conversations')
def api_get_convos():
    sess, err = session_required('agent')
    if err: return err
    convos = get_conversations()
    # Strip messages for list view (just metadata)
    lite = []
    for c in convos:
        lite.append({k: v for k, v in c.items() if k != 'messages'})
    return jsonify(lite)

@app.route('/chat/conversation/<cid>')
def api_get_convo(cid):
    sess, err = session_required('agent')
    if err: return err
    conv = get_messages(cid, mark_read_for='agent')
    if not conv: return jsonify({'error': 'Not found'}), 404
    return jsonify(conv)

@app.route('/chat/send', methods=['POST'])
def api_chat_send():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    ok, result = send_message(
        body.get('conversation_id',''),
        'agent',
        sess['name'],
        body.get('text','')
    )
    return jsonify({'success': True, 'message': result}) if ok else (jsonify({'success': False, 'error': result}), 400)

@app.route('/chat/start', methods=['POST'])
def api_chat_start():
    sess, err = session_required('agent')
    if err: return err
    body = request.get_json(silent=True) or {}
    conv = get_or_create_conversation(
        body.get('client_type','buyer'),
        body.get('client_id',''),
        body.get('client_name','Client')
    )
    return jsonify({'success': True, 'conversation_id': conv['id']})

@app.route('/chat/unread_count')
def api_chat_unread():
    sess, err = session_required('agent')
    if err: return err
    return jsonify({'count': get_total_unread_for_agents()})

# ── Client portal chat endpoints ──
@app.route('/portal/chat')
def api_portal_chat():
    tok  = request.cookies.get('serenia_client_token','')
    sess = get_client_session(tok)
    if not sess: return jsonify({'error': 'Not logged in'}), 401
    conv = get_client_conversation(sess['person_type'], sess['person_id'])
    if not conv:
        # Create conversation
        from data import load_data
        d = load_data()
        ptype = sess['person_type']
        pid   = sess['person_id']
        people = d.get('buyers', []) if ptype == 'buyer' else d.get('sellers', [])
        person = next((p for p in people if p['id'] == pid), {})
        name   = person.get('buyer_name') or person.get('seller_name') or sess['username']
        conv   = get_or_create_conversation(ptype, pid, name)
    conv = get_messages(conv['id'], mark_read_for='client')
    return jsonify(conv)

@app.route('/portal/chat/send', methods=['POST'])
def api_portal_chat_send():
    tok  = request.cookies.get('serenia_client_token','')
    sess = get_client_session(tok)
    if not sess: return jsonify({'error': 'Not logged in'}), 401
    body = request.get_json(silent=True) or {}
    conv = get_client_conversation(sess['person_type'], sess['person_id'])
    if not conv:
        from data import load_data
        d      = load_data()
        ptype  = sess['person_type']
        pid    = sess['person_id']
        people = d.get('buyers',[]) if ptype=='buyer' else d.get('sellers',[])
        person = next((p for p in people if p['id']==pid), {})
        name   = person.get('buyer_name') or person.get('seller_name') or sess['username']
        conv   = get_or_create_conversation(ptype, pid, name)
    ok, result = send_message(conv['id'], 'client', sess['username'], body.get('text',''))
    return jsonify({'success': True, 'message': result}) if ok else (jsonify({'success': False, 'error': result}), 400)

# ── New page routes ──
@app.route('/get_api_key_status')
def api_get_key_status():
    sess, err = session_required('admin')
    if err: return err
    import json as _j
    cfg_path = os.path.join(SERENIA_DIR, 'api_keys.json')
    try:
        with open(cfg_path) as f:
            cfg = _j.load(f)
        has_key = bool(cfg.get('anthropic_api_key','').strip())
    except:
        has_key = bool(os.environ.get('ANTHROPIC_API_KEY','').strip())
    return jsonify({'has_key': has_key})

@app.route('/save_api_key', methods=['POST'])
def api_save_key():
    sess, err = session_required('admin')
    if err: return err
    import json as _j
    body = request.get_json(silent=True) or {}
    key  = body.get('api_key','').strip()
    if not key: return jsonify({'success':False,'error':'Empty key'}), 400
    cfg_path = os.path.join(SERENIA_DIR, 'api_keys.json')
    try:
        try:
            with open(cfg_path) as f: cfg = _j.load(f)
        except: cfg = {}
        cfg['anthropic_api_key'] = key
        with open(cfg_path, 'w') as f: _j.dump(cfg, f)
        # Also set in current process
        os.environ['ANTHROPIC_API_KEY'] = key
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/ai_tools')
def ai_tools():     return _protected_page('ai_tools.html')

# ════════════════════════════════════════

if __name__ == '__main__':
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except:
        local_ip = '127.0.0.1'

    print('=' * 60)
    print('  SERENIA is starting...')
    print(f'  Local:    http://localhost:7777')
    print(f'  Network:  http://{local_ip}:7777')
    print(f'  Finance:  http://localhost:7777/fin/')
    print(f'  Admin:    http://localhost:7777/admin')
    print('  Default login — username: admin  password: admin123')
    print('=' * 60)

    app.run(host='0.0.0.0', debug=False, use_reloader=False, port=7777)
