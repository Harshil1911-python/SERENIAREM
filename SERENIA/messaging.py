import os
import json
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from data import load_data, save_data

SERENIA_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(SERENIA_DIR, 'msg_settings.json')

# ── Settings helpers ──────────────────────────────────────

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {'gmail': '', 'app_password': '', 'sender_name': 'SERENIA'}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {'gmail': '', 'app_password': '', 'sender_name': 'SERENIA'}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True, None
    except Exception as e:
        return False, str(e)

# ── Build recipient list ──────────────────────────────────

def get_all_recipients():
    """Return all sellers + buyers with email or phone."""
    data    = load_data()
    sellers = data.get('sellers', [])
    buyers  = data.get('buyers',  [])
    result  = []

    for s in sellers:
        result.append({
            'id':    s.get('id'),
            'name':  s.get('seller_name', ''),
            'email': s.get('email', ''),
            'phone': s.get('phone', ''),
            'type':  'Seller',
            'role':  s.get('role', ''),
        })

    for b in buyers:
        result.append({
            'id':    b.get('id'),
            'name':  b.get('buyer_name', ''),
            'email': b.get('email', ''),
            'phone': b.get('phone', ''),
            'type':  'Buyer',
            'intent': b.get('intent', ''),
        })

    return result

# ── Personalization ───────────────────────────────────────

def personalize(template, recipient):
    """Replace {{name}}, {{type}}, {{role}} placeholders."""
    msg = template
    msg = msg.replace('{{name}}',  recipient.get('name',  'Client'))
    msg = msg.replace('{{type}}',  recipient.get('type',  'Client'))
    msg = msg.replace('{{role}}',  recipient.get('role',  recipient.get('intent', '')))
    msg = msg.replace('{{email}}', recipient.get('email', ''))
    msg = msg.replace('{{phone}}', recipient.get('phone', ''))
    return msg

# ── Send single email ─────────────────────────────────────

def send_email(gmail, app_password, sender_name, to_email, subject, body_html):
    """Send via Gmail SMTP. Returns (True, None) or (False, error)."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{sender_name} <{gmail}>"
        msg['To']      = to_email

        # Plain text fallback
        plain = body_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        import re
        plain = re.sub(r'<[^>]+>', '', plain)
        msg.attach(MIMEText(plain,     'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(gmail, app_password)
            server.send_message(msg)

        return True, None
    except smtplib.SMTPAuthenticationError:
        return False, 'Gmail authentication failed. Check your email and App Password.'
    except smtplib.SMTPRecipientsRefused:
        return False, f'Recipient refused: {to_email}'
    except Exception as e:
        return False, str(e)

# ── Bulk send (runs in thread, reports progress) ──────────

_bulk_jobs = {}  # job_id → {total, sent, failed, errors, done}

def start_bulk_send(job_id, recipients, subject, template, settings):
    """Launch bulk email in background thread. Track via job_id."""
    _bulk_jobs[job_id] = {
        'total':  len(recipients),
        'sent':   0,
        'failed': 0,
        'errors': [],
        'done':   False,
        'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    def worker():
        gmail     = settings.get('gmail', '')
        app_pw    = settings.get('app_password', '')
        sndr_name = settings.get('sender_name', 'SERENIA')

        for r in recipients:
            email = r.get('email', '').strip()
            if not email:
                _bulk_jobs[job_id]['failed'] += 1
                _bulk_jobs[job_id]['errors'].append(f"{r.get('name','?')}: No email address")
                continue

            body = personalize(template, r)
            ok, err = send_email(gmail, app_pw, sndr_name, email, subject, body)

            if ok:
                _bulk_jobs[job_id]['sent'] += 1
            else:
                _bulk_jobs[job_id]['failed'] += 1
                _bulk_jobs[job_id]['errors'].append(f"{r.get('name','?')} ({email}): {err}")

        _bulk_jobs[job_id]['done'] = True
        print(f"[SERENIA] Bulk send {job_id} done — sent:{_bulk_jobs[job_id]['sent']} failed:{_bulk_jobs[job_id]['failed']}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()

def get_bulk_status(job_id):
    return _bulk_jobs.get(job_id)
