import os, json
from werkzeug.utils import secure_filename

SERENIA_DIR    = os.path.dirname(os.path.abspath(__file__))
BRANDING_FILE  = os.path.join(SERENIA_DIR, 'branding.json')
LOGO_DIR       = os.path.join(SERENIA_DIR, 'photos')

DEFAULT = {
    'company_name':  'SERENIA',
    'tagline':       'Real Estate Management',
    'primary_color': '#1400cc',
    'accent_color':  '#5B21F5',
    'logo_filename': '',
    'phone':         '',
    'email':         '',
    'address':       '',
    'website':       '',
    'whatsapp':      '',
}

def load_branding():
    if not os.path.exists(BRANDING_FILE):
        return dict(DEFAULT)
    try:
        with open(BRANDING_FILE, 'r') as f:
            b = json.load(f)
            return {**DEFAULT, **b}
    except:
        return dict(DEFAULT)

def save_branding(data, logo_file=None):
    try:
        b = load_branding()
        allowed = set(DEFAULT.keys())
        for k, v in data.items():
            if k in allowed:
                b[k] = v
        if logo_file and logo_file.filename:
            fname = 'company_logo_' + secure_filename(logo_file.filename)
            logo_file.save(os.path.join(LOGO_DIR, fname))
            b['logo_filename'] = fname
        with open(BRANDING_FILE, 'w') as f:
            json.dump(b, f, indent=2)
        return True, None
    except Exception as e:
        return False, str(e)
