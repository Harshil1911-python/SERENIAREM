import os
import uuid
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from data import load_data, save_data

SERENIA_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR  = os.path.join(SERENIA_DIR, 'photos')
VIDEOS_DIR  = os.path.join(SERENIA_DIR, 'videos')

def init_folders():
    """Create photos/ and videos/ folders if they don't exist."""
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    os.makedirs(VIDEOS_DIR, exist_ok=True)

def get_all_properties():
    """Return list of all properties."""
    data = load_data()
    return data['properties']

def save_property(form_data_raw, photo_files, video_files):
    """
    Parse form data, save uploaded files, append to data.dat.
    Returns (prop_id, None) on success or (None, error_message) on failure.
    """
    try:
        prop = json.loads(form_data_raw)

        # Assign unique ID and timestamp
        prop['id']         = str(uuid.uuid4())[:8].upper()
        prop['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save photos
        saved_photos = []
        for photo in photo_files:
            if photo and photo.filename:
                fname = f"{prop['id']}_{secure_filename(photo.filename)}"
                photo.save(os.path.join(PHOTOS_DIR, fname))
                saved_photos.append(fname)
        prop['photos'] = saved_photos

        # Save videos
        saved_videos = []
        for video in video_files:
            if video and video.filename:
                fname = f"{prop['id']}_{secure_filename(video.filename)}"
                video.save(os.path.join(VIDEOS_DIR, fname))
                saved_videos.append(fname)
        prop['videos'] = saved_videos

        # Append to data.dat
        data = load_data()
        data['properties'].append(prop)
        save_data(data)

        print(f"[SERENIA] Property saved: {prop['id']} — {prop.get('title', 'Untitled')}")
        return prop['id'], None

    except Exception as e:
        print(f"[SERENIA] Error saving property: {e}")
        return None, str(e)

def update_property(prop_id, form_data_raw, new_photo_files, new_video_files):
    """Update an existing property. New files are appended, removed ones are deleted."""
    try:
        updates = json.loads(form_data_raw)
        data    = load_data()
        props   = data.get('properties', [])
        idx     = next((i for i, p in enumerate(props) if p.get('id') == prop_id), None)
        if idx is None:
            return False, 'Property not found'

        prop = props[idx]

        # ── Remove photos that user deleted ──
        removed_photos = updates.pop('removed_photos', [])
        removed_videos = updates.pop('removed_videos', [])

        if removed_photos:
            prop['photos'] = [f for f in prop.get('photos', []) if f not in removed_photos]
            # Optionally delete files from disk
            for fname in removed_photos:
                fpath = os.path.join(PHOTOS_DIR, fname)
                if os.path.exists(fpath):
                    try: os.remove(fpath)
                    except: pass

        if removed_videos:
            prop['videos'] = [f for f in prop.get('videos', []) if f not in removed_videos]
            for fname in removed_videos:
                fpath = os.path.join(VIDEOS_DIR, fname)
                if os.path.exists(fpath):
                    try: os.remove(fpath)
                    except: pass

        # ── Save new photos ──
        for photo in new_photo_files:
            if photo and photo.filename:
                fname = f"{prop_id}_{secure_filename(photo.filename)}"
                photo.save(os.path.join(PHOTOS_DIR, fname))
                prop.setdefault('photos', []).append(fname)

        # ── Save new videos ──
        for video in new_video_files:
            if video and video.filename:
                fname = f"{prop_id}_{secure_filename(video.filename)}"
                video.save(os.path.join(VIDEOS_DIR, fname))
                prop.setdefault('videos', []).append(fname)

        # ── Update other fields (protect id, created_at, photos, videos) ──
        protected = {'id', 'created_at', 'photos', 'videos'}
        for k, v in updates.items():
            if k not in protected:
                prop[k] = v

        prop['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        props[idx] = prop
        data['properties'] = props
        save_data(data)
        print(f"[SERENIA] Property updated: {prop_id}")
        return True, None
    except Exception as e:
        print(f"[SERENIA] Error updating property: {e}")
        return False, str(e)

def remove_property_file(prop_id, filename, file_type):
    """Remove a single photo or video from a property and delete from disk."""
    try:
        data  = load_data()
        props = data.get('properties', [])
        idx   = next((i for i, p in enumerate(props) if p.get('id') == prop_id), None)
        if idx is None:
            return False, 'Property not found'
        key = 'photos' if file_type == 'photo' else 'videos'
        props[idx][key] = [f for f in props[idx].get(key, []) if f != filename]
        data['properties'] = props
        save_data(data)
        # Delete physical file
        folder = 'photos' if file_type == 'photo' else 'videos'
        fpath  = os.path.join(SERENIA_DIR, folder, filename)
        if os.path.exists(fpath):
            os.remove(fpath)
        return True, None
    except Exception as e:
        return False, str(e)

def delete_property(prop_id):
    """Remove a property and all its files from disk."""
    try:
        data = load_data()
        original_count = len(data.get('properties', []))
        prop = next((p for p in data.get('properties', []) if p.get('id') == prop_id), None)
        if not prop:
            return False, 'Property not found'
        # Delete photos and videos from disk
        for fname in prop.get('photos', []):
            fpath = os.path.join(SERENIA_DIR, 'photos', fname)
            if os.path.exists(fpath): os.remove(fpath)
        for fname in prop.get('videos', []):
            fpath = os.path.join(SERENIA_DIR, 'videos', fname)
            if os.path.exists(fpath): os.remove(fpath)
        data['properties'] = [p for p in data['properties'] if p.get('id') != prop_id]
        save_data(data)
        print(f"[SERENIA] Property deleted: {prop_id}")
        return True, None
    except Exception as e:
        print(f"[SERENIA] Error deleting property: {e}")
        return False, str(e)
