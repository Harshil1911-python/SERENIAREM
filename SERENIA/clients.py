import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from data import load_data, save_data

SERENIA_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Folder helpers ──────────────────────────────

def _person_doc_dir(folder_root, person_name):
    """Return path to a person's docs folder under folder_root, creating it."""
    safe = secure_filename(person_name) or 'unknown'
    path = os.path.join(SERENIA_DIR, folder_root, safe)
    os.makedirs(path, exist_ok=True)
    return path, safe

def init_client_folders():
    os.makedirs(os.path.join(SERENIA_DIR, 'seller_docs'), exist_ok=True)
    os.makedirs(os.path.join(SERENIA_DIR, 'buyer_docs'),  exist_ok=True)

def _delete_person_files(folder_root, person):
    """Delete all photos and doc files for a person from disk."""
    try:
        name = person.get('seller_name') or person.get('buyer_name') or person.get('emp_name') or 'unknown'
        safe = secure_filename(name) or 'unknown'
        folder = os.path.join(SERENIA_DIR, folder_root, safe)
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder, ignore_errors=True)
    except: pass

# ── CLIENTS (combined total) ────────────────────

def get_all_clients():
    return load_data().get('clients', [])

# ════════════════════════════════════════════════
#  SELLERS
# ════════════════════════════════════════════════

def get_all_sellers():
    return load_data().get('sellers', [])

def save_seller(form_data_raw, photo_file, doc_photo_files):
    try:
        seller = json.loads(form_data_raw)
        seller['id']         = str(uuid.uuid4())[:8].upper()
        seller['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        doc_dir, safe_name = _person_doc_dir('seller_docs', seller.get('seller_name', 'unknown'))

        # Profile photo
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            seller['photo_filename'] = fname
        else:
            seller['photo_filename'] = None

        # Document photos
        saved_docs = []
        for f in doc_photo_files:
            if f and f.filename:
                fname = f"doc_{secure_filename(f.filename)}"
                f.save(os.path.join(doc_dir, fname))
                saved_docs.append(fname)
        seller['doc_photo_filenames'] = saved_docs
        seller['doc_folder']          = safe_name

        data = load_data()
        data.setdefault('sellers', []).append(seller)
        data.setdefault('clients', []).append({
            'id': seller['id'], 'type': 'seller',
            'name': seller.get('seller_name', ''), 'created_at': seller['created_at'],
        })
        save_data(data)
        print(f"[SERENIA] Seller saved: {seller['id']} — {seller.get('seller_name','')}")
        return seller['id'], None
    except Exception as e:
        print(f"[SERENIA] Error saving seller: {e}")
        return None, str(e)

def delete_seller(seller_id):
    try:
        data = load_data()
        seller = next((s for s in data.get('sellers',[]) if s.get('id')==seller_id), None)
        if not seller: return False, 'Seller not found'
        # Delete photo files from disk
        _delete_person_files('seller_docs', seller)
        data['sellers'] = [s for s in data.get('sellers',[]) if s.get('id')!=seller_id]
        data['clients'] = [c for c in data.get('clients',[]) if c.get('id')!=seller_id]
        save_data(data)
        return True, None
    except Exception as e:
        return False, str(e)

# ════════════════════════════════════════════════
#  BUYERS
# ════════════════════════════════════════════════

def get_all_buyers():
    return load_data().get('buyers', [])

def save_buyer(form_data_raw, photo_file, doc_photo_files):
    try:
        buyer = json.loads(form_data_raw)
        buyer['id']         = str(uuid.uuid4())[:8].upper()
        buyer['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        doc_dir, safe_name = _person_doc_dir('buyer_docs', buyer.get('buyer_name', 'unknown'))

        # Profile photo
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            buyer['photo_filename'] = fname
        else:
            buyer['photo_filename'] = None

        # Document photos
        saved_docs = []
        for f in doc_photo_files:
            if f and f.filename:
                fname = f"doc_{secure_filename(f.filename)}"
                f.save(os.path.join(doc_dir, fname))
                saved_docs.append(fname)
        buyer['doc_photo_filenames'] = saved_docs
        buyer['doc_folder']          = safe_name

        data = load_data()
        data.setdefault('buyers', []).append(buyer)
        data.setdefault('clients', []).append({
            'id': buyer['id'], 'type': 'buyer',
            'name': buyer.get('buyer_name', ''), 'created_at': buyer['created_at'],
        })
        save_data(data)
        print(f"[SERENIA] Buyer saved: {buyer['id']} — {buyer.get('buyer_name','')}")
        return buyer['id'], None
    except Exception as e:
        print(f"[SERENIA] Error saving buyer: {e}")
        return None, str(e)

def delete_buyer(buyer_id):
    try:
        data = load_data()
        buyer = next((b for b in data.get('buyers',[]) if b.get('id')==buyer_id), None)
        if not buyer: return False, 'Buyer not found'
        _delete_person_files('buyer_docs', buyer)
        data['buyers']  = [b for b in data.get('buyers',[])  if b.get('id')!=buyer_id]
        data['clients'] = [c for c in data.get('clients',[]) if c.get('id')!=buyer_id]
        save_data(data)
        print(f"[SERENIA] Buyer deleted: {buyer_id}")
        return True, None
    except Exception as e:
        return False, str(e)

# ════════════════════════════════════════════════
#  UPDATE FUNCTIONS
# ════════════════════════════════════════════════

def update_seller(seller_id, form_data_raw, photo_file, doc_photo_files):
    """Update an existing seller."""
    try:
        updates = json.loads(form_data_raw)
        data    = load_data()
        sellers = data.get('sellers', [])
        idx     = next((i for i, s in enumerate(sellers) if s.get('id') == seller_id), None)
        if idx is None:
            return False, 'Seller not found'

        seller  = sellers[idx]
        doc_dir, _ = _person_doc_dir('seller_docs', seller.get('seller_name', 'unknown'))

        # Remove profile photo if requested
        if updates.pop('remove_profile_photo', False):
            if seller.get('photo_filename'):
                fp = os.path.join(doc_dir, seller['photo_filename'])
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass
            seller['photo_filename'] = None

        # New profile photo (replace)
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            seller['photo_filename'] = fname

        # Remove existing doc photos
        removed_docs = updates.pop('removed_doc_photos', [])
        if removed_docs:
            seller['doc_photo_filenames'] = [
                f for f in seller.get('doc_photo_filenames', []) if f not in removed_docs
            ]
            for fname in removed_docs:
                fp = os.path.join(doc_dir, fname)
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass

        # New doc photos (append)
        for f in doc_photo_files:
            if f and f.filename:
                fname = f"doc_{secure_filename(f.filename)}"
                f.save(os.path.join(doc_dir, fname))
                seller.setdefault('doc_photo_filenames', []).append(fname)

        protected = {'id', 'created_at', 'photo_filename', 'doc_photo_filenames', 'doc_folder'}
        for k, v in updates.items():
            if k not in protected:
                seller[k] = v

        seller['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sellers[idx] = seller

        for c in data.get('clients', []):
            if c.get('id') == seller_id:
                c['name'] = seller.get('seller_name', c['name'])

        data['sellers'] = sellers
        save_data(data)
        print(f"[SERENIA] Seller updated: {seller_id}")
        return True, None
    except Exception as e:
        print(f"[SERENIA] Error updating seller: {e}")
        return False, str(e)

def update_buyer(buyer_id, form_data_raw, photo_file, doc_photo_files):
    """Update an existing buyer."""
    try:
        updates = json.loads(form_data_raw)
        data    = load_data()
        buyers  = data.get('buyers', [])
        idx     = next((i for i, b in enumerate(buyers) if b.get('id') == buyer_id), None)
        if idx is None:
            return False, 'Buyer not found'

        buyer   = buyers[idx]
        doc_dir, _ = _person_doc_dir('buyer_docs', buyer.get('buyer_name', 'unknown'))

        # Remove profile photo if requested
        if updates.pop('remove_profile_photo', False):
            if buyer.get('photo_filename'):
                fp = os.path.join(doc_dir, buyer['photo_filename'])
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass
            buyer['photo_filename'] = None

        # New profile photo (replace)
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            buyer['photo_filename'] = fname

        # Remove existing doc photos
        removed_docs = updates.pop('removed_doc_photos', [])
        if removed_docs:
            buyer['doc_photo_filenames'] = [
                f for f in buyer.get('doc_photo_filenames', []) if f not in removed_docs
            ]
            for fname in removed_docs:
                fp = os.path.join(doc_dir, fname)
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass

        # New doc photos (append)
        for f in doc_photo_files:
            if f and f.filename:
                fname = f"doc_{secure_filename(f.filename)}"
                f.save(os.path.join(doc_dir, fname))
                buyer.setdefault('doc_photo_filenames', []).append(fname)

        protected = {'id', 'created_at', 'photo_filename', 'doc_photo_filenames', 'doc_folder'}
        for k, v in updates.items():
            if k not in protected:
                buyer[k] = v

        buyer['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        buyers[idx] = buyer

        for c in data.get('clients', []):
            if c.get('id') == buyer_id:
                c['name'] = buyer.get('buyer_name', c['name'])

        data['buyers'] = buyers
        save_data(data)
        print(f"[SERENIA] Buyer updated: {buyer_id}")
        return True, None
    except Exception as e:
        print(f"[SERENIA] Error updating buyer: {e}")
        return False, str(e)
