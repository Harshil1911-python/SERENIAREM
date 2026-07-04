from datetime import datetime, date
from data import load_data

def get_notifications():
    """Build notification list from tasks, viewings, doc expiries, deals."""
    try:
        d     = load_data()
        today = date.today().isoformat()
        notifs = []

        # ── Overdue tasks ──
        for t in d.get('tasks', []):
            if t.get('status') == 'Done': continue
            due = t.get('due_date', '')
            if due and due < today:
                notifs.append({
                    'type':    'overdue_task',
                    'icon':    '⏰',
                    'color':   'red',
                    'title':   f"Overdue Task: {t.get('title','')}",
                    'sub':     f"Was due {due}",
                    'link':    'tasks.html',
                    'id':      t.get('id'),
                    'time':    due,
                })
            elif due == today:
                notifs.append({
                    'type':    'task_today',
                    'icon':    '📌',
                    'color':   'amber',
                    'title':   f"Task Due Today: {t.get('title','')}",
                    'sub':     t.get('category', 'General'),
                    'link':    'tasks.html',
                    'id':      t.get('id'),
                    'time':    due,
                })

        # ── Today's viewings ──
        for v in d.get('viewings', []):
            if v.get('status') in ('Completed','Cancelled'): continue
            if v.get('date','') == today:
                prop_id = v.get('property_id','')
                props   = d.get('properties',[])
                prop    = next((p for p in props if p.get('id')==prop_id), None)
                notifs.append({
                    'type':  'viewing_today',
                    'icon':  '🏠',
                    'color': 'blue',
                    'title': f"Viewing Today: {prop.get('title','Property') if prop else 'Property'}",
                    'sub':   f"At {v.get('time','?')} — {v.get('status','Scheduled')}",
                    'link':  'viewings.html',
                    'id':    v.get('id'),
                    'time':  v.get('date',''),
                })

        # ── Expiring documents (≤ 30 days) ──
        for e in d.get('doc_expiries', []):
            exp_date = e.get('expiry_date','')
            if not exp_date: continue
            days = (date.fromisoformat(exp_date) - date.today()).days
            if days < 0:
                notifs.append({
                    'type':  'doc_expired',
                    'icon':  '🚨',
                    'color': 'red',
                    'title': f"Expired: {e.get('doc_type','')}",
                    'sub':   f"Person ID: {e.get('person_id','')} — expired {abs(days)}d ago",
                    'link':  'docexpiry.html',
                    'id':    e.get('id'),
                    'time':  exp_date,
                })
            elif days <= 30:
                notifs.append({
                    'type':  'doc_expiring',
                    'icon':  '⚠️',
                    'color': 'amber',
                    'title': f"Expiring Soon: {e.get('doc_type','')}",
                    'sub':   f"Expires in {days} day{'s' if days!=1 else ''}",
                    'link':  'docexpiry.html',
                    'id':    e.get('id'),
                    'time':  exp_date,
                })

        # ── Deals with no activity > 7 days ──
        for deal in d.get('deals', []):
            if deal.get('stage') in ('Closed Won','Closed Lost'): continue
            updated = deal.get('updated_at','') or deal.get('created_at','')
            if not updated: continue
            try:
                upd_date = datetime.strptime(updated[:10], '%Y-%m-%d').date()
                stale_days = (date.today() - upd_date).days
                if stale_days >= 7:
                    notifs.append({
                        'type':  'stale_deal',
                        'icon':  '📋',
                        'color': 'purple',
                        'title': f"Stale Deal: {deal.get('title','')}",
                        'sub':   f"No activity for {stale_days} days — Stage: {deal.get('stage','')}",
                        'link':  'deals.html',
                        'id':    deal.get('id'),
                        'time':  updated[:10],
                    })
            except: pass

        # Sort: red first, then amber, then others
        priority = {'red':0,'amber':1,'blue':2,'purple':3,'green':4}
        notifs.sort(key=lambda n: priority.get(n.get('color',''),99))

        return notifs[:50]  # cap at 50
    except Exception as e:
        return []
