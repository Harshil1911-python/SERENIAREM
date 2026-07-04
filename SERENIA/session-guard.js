/**
 * SERENIA Session Guard + Notification Bell
 * Include in every protected page: <script src="session-guard.js"></script>
 */

(async function() {
  try {
    const res  = await fetch('/me');
    const data = await res.json();

    if (!data.logged_in) {
      window.location.href = '/';
      return;
    }

    window.SERENIA_USER = data;

    const el = document.getElementById('userInfo');
    if (el) {
      const roleColors = { admin:'#f87171', manager:'#fbbf24', agent:'#818cf8' };
      const color = roleColors[data.role] || '#fff';
      el.innerHTML = `
        <div id="notifBellWrap" style="position:relative;display:inline-block;margin-right:12px">
          <button id="notifBell" onclick="toggleNotifPanel()" style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:8px;padding:5px 12px;cursor:pointer;font-size:1rem;position:relative;transition:background .2s" onmouseover="this.style.background='rgba(255,255,255,.2)'" onmouseout="this.style.background='rgba(255,255,255,.1)'">
            🔔
            <span id="notifCount" style="display:none;position:absolute;top:-5px;right:-5px;background:#f87171;color:#fff;border-radius:50%;width:18px;height:18px;font-size:.6rem;font-weight:900;display:flex;align-items:center;justify-content:center;font-family:'Nunito',sans-serif"></span>
          </button>
        </div>
        <span style="font-size:.8rem;font-weight:800;color:rgba(255,255,255,.5);text-transform:uppercase;letter-spacing:.06em">
          ${data.name}
          <span style="color:${color};margin-left:6px">[${data.role.toUpperCase()}]</span>
        </span>
        <button onclick="doLogout()" style="background:rgba(220,38,38,.2);border:1px solid rgba(220,38,38,.35);color:#f87171;font-family:'Nunito',sans-serif;font-weight:800;font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;padding:5px 12px;border-radius:8px;cursor:pointer;margin-left:12px;transition:background .2s" onmouseover="this.style.background='rgba(220,38,38,.35)'" onmouseout="this.style.background='rgba(220,38,38,.2)'">LOGOUT</button>
        ${data.role === 'admin' ? `<button onclick="window.location.href='/admin'" style="background:rgba(129,140,248,.15);border:1px solid rgba(129,140,248,.25);color:#818cf8;font-family:'Nunito',sans-serif;font-weight:800;font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;padding:5px 12px;border-radius:8px;cursor:pointer;margin-left:6px;transition:background .2s" onmouseover="this.style.background='rgba(129,140,248,.25)'" onmouseout="this.style.background='rgba(129,140,248,.15)'">USERS</button>` : ''}
      `;

      // Inject notification panel into body
      const panel = document.createElement('div');
      panel.id = 'notifPanel';
      panel.style.cssText = `
        display:none;position:fixed;top:54px;right:16px;width:360px;max-height:520px;
        background:#1e1e3a;border:1px solid rgba(255,255,255,.12);border-radius:16px;
        box-shadow:0 12px 40px rgba(0,0,0,.6);z-index:9999;overflow:hidden;
        flex-direction:column;font-family:'Nunito',sans-serif;
      `;
      panel.innerHTML = `
        <div style="background:#1400cc;padding:12px 16px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0">
          <span style="font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:.07em;color:#fff">🔔 NOTIFICATIONS</span>
          <button onclick="document.getElementById('notifPanel').style.display='none'" style="background:rgba(255,255,255,.15);border:none;color:#fff;border-radius:6px;padding:3px 8px;cursor:pointer;font-size:.85rem">✕</button>
        </div>
        <div id="notifList" style="overflow-y:auto;flex:1;max-height:440px;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.1) transparent">
          <div style="text-align:center;padding:24px;color:rgba(255,255,255,.3);font-weight:700;font-size:.85rem">Loading…</div>
        </div>
      `;
      document.body.appendChild(panel);

      // Close panel when clicking outside
      document.addEventListener('click', e => {
        const p = document.getElementById('notifPanel');
        const b = document.getElementById('notifBell');
        if (p && b && !p.contains(e.target) && !b.contains(e.target)) {
          p.style.display = 'none';
        }
      });

      // Load notifications
      loadNotifications();
    }

    // Role-based element hiding
    const roleLevel = { agent:1, manager:2, admin:3 };
    const userLevel = roleLevel[data.role] || 0;
    document.querySelectorAll('.admin-only').forEach(el => { if (userLevel < 3) el.style.display = 'none'; });
    document.querySelectorAll('.manager-only').forEach(el => { if (userLevel < 2) el.style.display = 'none'; });

  } catch(e) {
    window.location.href = '/';
  }
})();

async function loadNotifications() {
  try {
    const res   = await fetch('/get_notifications');
    const notifs = await res.json();

    // Update bell badge
    const count = notifs.filter(n => n.color === 'red' || n.color === 'amber').length;
    const badge = document.getElementById('notifCount');
    if (badge) {
      if (count > 0) {
        badge.style.display = 'flex';
        badge.textContent   = count > 9 ? '9+' : count;
      } else {
        badge.style.display = 'none';
      }
    }

    // Render panel
    const list = document.getElementById('notifList');
    if (!list) return;

    if (!notifs.length) {
      list.innerHTML = `<div style="text-align:center;padding:32px;color:rgba(255,255,255,.25);font-weight:700;font-size:.85rem">✅ All clear — no alerts</div>`;
      return;
    }

    const colorMap = {
      red:    { bg:'rgba(220,38,38,.12)',   border:'rgba(220,38,38,.25)',   text:'#f87171' },
      amber:  { bg:'rgba(217,119,6,.1)',    border:'rgba(217,119,6,.2)',    text:'#fbbf24' },
      blue:   { bg:'rgba(20,0,204,.15)',    border:'rgba(20,0,204,.3)',     text:'#818cf8' },
      purple: { bg:'rgba(124,58,237,.12)',  border:'rgba(124,58,237,.25)',  text:'#c4b5fd' },
      green:  { bg:'rgba(22,163,74,.1)',    border:'rgba(22,163,74,.2)',    text:'#4ade80' },
    };

    list.innerHTML = notifs.map(n => {
      const c = colorMap[n.color] || colorMap.blue;
      return `
        <div onclick="window.location.href='${n.link}'" style="
          display:flex;align-items:flex-start;gap:12px;padding:12px 16px;
          border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer;
          transition:background .18s;
        " onmouseover="this.style.background='rgba(255,255,255,.04)'" onmouseout="this.style.background=''">
          <div style="
            width:34px;height:34px;border-radius:50%;flex-shrink:0;
            background:${c.bg};border:1px solid ${c.border};
            display:flex;align-items:center;justify-content:center;font-size:1rem;margin-top:1px
          ">${n.icon}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:.84rem;font-weight:800;color:#fff;margin-bottom:2px;line-height:1.3">${n.title}</div>
            <div style="font-size:.72rem;font-weight:700;color:rgba(255,255,255,.4)">${n.sub}</div>
          </div>
          <div style="font-size:.65rem;font-weight:700;color:rgba(255,255,255,.25);flex-shrink:0;margin-top:2px">${n.time||''}</div>
        </div>`;
    }).join('');

  } catch(e) {
    const list = document.getElementById('notifList');
    if (list) list.innerHTML = `<div style="text-align:center;padding:24px;color:rgba(255,255,255,.25);font-size:.82rem;font-weight:700">Failed to load</div>`;
  }
}

function toggleNotifPanel() {
  const p = document.getElementById('notifPanel');
  if (!p) return;
  const isOpen = p.style.display === 'flex';
  p.style.display = isOpen ? 'none' : 'flex';
  if (!isOpen) loadNotifications(); // refresh on open
}

async function doLogout() {
  await fetch('/logout', { method: 'POST' });
  window.location.href = '/';
}
