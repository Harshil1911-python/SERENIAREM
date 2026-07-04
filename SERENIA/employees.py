import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from data import load_data, save_data

SERENIA_DIR = os.path.dirname(os.path.abspath(__file__))

def init_emp_folders():
    os.makedirs(os.path.join(SERENIA_DIR, 'emp_docs'), exist_ok=True)

def _emp_doc_dir(emp_name):
    safe = secure_filename(emp_name) or 'unknown_emp'
    path = os.path.join(SERENIA_DIR, 'emp_docs', safe)
    os.makedirs(path, exist_ok=True)
    return path, safe

def get_all_employees():
    return load_data().get('employees', [])

def save_employee(form_data_raw, photo_file, doc_photo_files):
    try:
        emp = json.loads(form_data_raw)
        emp['id']         = str(uuid.uuid4())[:8].upper()
        emp['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        doc_dir, safe_name = _emp_doc_dir(emp.get('emp_name', 'unknown'))

        # Profile photo
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            emp['photo_filename'] = fname
        else:
            emp['photo_filename'] = None

        # Doc photos
        saved_docs = []
        for f in doc_photo_files:
            if f and f.filename:
                fname = f"doc_{secure_filename(f.filename)}"
                f.save(os.path.join(doc_dir, fname))
                saved_docs.append(fname)
        emp['doc_photo_filenames'] = saved_docs
        emp['doc_folder']          = safe_name

        data = load_data()
        data.setdefault('employees', []).append(emp)
        save_data(data)

        print(f"[SERENIA] Employee saved: {emp['id']} — {emp.get('emp_name','')}")
        return emp['id'], None
    except Exception as e:
        print(f"[SERENIA] Error saving employee: {e}")
        return None, str(e)

def delete_employee(emp_id):
    try:
        data = load_data()
        emp  = next((e for e in data.get('employees',[]) if e.get('id')==emp_id), None)
        if not emp: return False, 'Employee not found'
        # Delete all employee docs/photos from disk
        try:
            safe = secure_filename(emp.get('emp_name','unknown')) or 'unknown_emp'
            folder = os.path.join(SERENIA_DIR, 'emp_docs', safe)
            if os.path.exists(folder):
                import shutil
                shutil.rmtree(folder, ignore_errors=True)
        except: pass
        data['employees'] = [e for e in data.get('employees',[]) if e.get('id')!=emp_id]
        save_data(data)
        print(f"[SERENIA] Employee deleted: {emp_id}")
        return True, None
    except Exception as e:
        return False, str(e)

def update_employee_status(emp_id, status):
    """Toggle Active / Inactive."""
    try:
        data = load_data()
        for e in data.get('employees', []):
            if e.get('id') == emp_id:
                e['status'] = status
                save_data(data)
                print(f"[SERENIA] Employee {emp_id} status → {status}")
                return True, None
        return False, 'Employee not found'
    except Exception as e:
        return False, str(e)

def update_employee(emp_id, form_data_raw, photo_file, doc_photo_files):
    """Update an existing employee."""
    try:
        updates = json.loads(form_data_raw)
        data    = load_data()
        emps    = data.get('employees', [])
        idx     = next((i for i, e in enumerate(emps) if e.get('id') == emp_id), None)
        if idx is None:
            return False, 'Employee not found'

        emp     = emps[idx]
        doc_dir, _ = _emp_doc_dir(emp.get('emp_name', 'unknown'))

        # Remove profile photo if requested
        if updates.pop('remove_profile_photo', False):
            if emp.get('photo_filename'):
                fp = os.path.join(doc_dir, emp['photo_filename'])
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except: pass
            emp['photo_filename'] = None

        # New profile photo (replace)
        if photo_file and photo_file.filename:
            fname = f"photo_{secure_filename(photo_file.filename)}"
            photo_file.save(os.path.join(doc_dir, fname))
            emp['photo_filename'] = fname

        # Remove existing doc photos
        removed_docs = updates.pop('removed_doc_photos', [])
        if removed_docs:
            emp['doc_photo_filenames'] = [
                f for f in emp.get('doc_photo_filenames', []) if f not in removed_docs
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
                emp.setdefault('doc_photo_filenames', []).append(fname)

        protected = {'id', 'created_at', 'photo_filename', 'doc_photo_filenames', 'doc_folder'}
        for k, v in updates.items():
            if k not in protected:
                emp[k] = v

        emp['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        emps[idx] = emp
        data['employees'] = emps
        save_data(data)
        print(f"[SERENIA] Employee updated: {emp_id}")
        return True, None
    except Exception as e:
        print(f"[SERENIA] Error updating employee: {e}")
        return False, str(e)
