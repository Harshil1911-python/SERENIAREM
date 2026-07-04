import os, json, zipfile, io, shutil
from datetime import datetime
from data import load_data, save_data

SERENIA_DIR = os.path.dirname(os.path.abspath(__file__))

def create_backup():
    """Create a ZIP backup of data.dat + all uploaded files. Returns BytesIO."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        # data.dat
        dat = os.path.join(SERENIA_DIR, 'data.dat')
        if os.path.exists(dat):
            zf.write(dat, 'data.dat')

        # msg_settings.json
        cfg = os.path.join(SERENIA_DIR, 'msg_settings.json')
        if os.path.exists(cfg):
            zf.write(cfg, 'msg_settings.json')

        # branding.json
        branding = os.path.join(SERENIA_DIR, 'branding.json')
        if os.path.exists(branding):
            zf.write(branding, 'branding.json')

        # Photos and videos
        for folder in ['photos', 'videos', 'seller_docs', 'buyer_docs', 'emp_docs']:
            folder_path = os.path.join(SERENIA_DIR, folder)
            if os.path.exists(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        filepath  = os.path.join(root, file)
                        arcname   = os.path.relpath(filepath, SERENIA_DIR)
                        zf.write(filepath, arcname)

    buf.seek(0)
    return buf

def restore_backup(zip_bytes):
    """Restore from a ZIP backup. Returns (True, None) or (False, error)."""
    try:
        buf = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(buf, 'r') as zf:
            names = zf.namelist()
            if 'data.dat' not in names:
                return False, 'Invalid backup file — data.dat not found'

            # Validate data.dat is valid JSON
            raw = zf.read('data.dat').decode('utf-8')
            json.loads(raw)  # will raise if invalid

            # Extract all files to SERENIA_DIR
            for name in names:
                target = os.path.join(SERENIA_DIR, name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(name) as src, open(target, 'wb') as dst:
                    dst.write(src.read())

        return True, None
    except json.JSONDecodeError:
        return False, 'Backup data.dat is corrupted (invalid JSON)'
    except Exception as e:
        return False, str(e)

def get_backup_info():
    """Return info about current data for backup summary."""
    try:
        d = load_data()
        return {
            'properties': len(d.get('properties', [])),
            'sellers':    len(d.get('sellers', [])),
            'buyers':     len(d.get('buyers', [])),
            'employees':  len(d.get('employees', [])),
            'deals':      len(d.get('deals', [])),
            'tasks':      len(d.get('tasks', [])),
            'viewings':   len(d.get('viewings', [])),
            'payments':   len(d.get('payments', [])),
            'leads':      len(d.get('leads', [])),
            'timestamp':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    except:
        return {}
