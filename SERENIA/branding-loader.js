/**
 * SERENIA Branding Loader v2
 * Injects a <style> tag that overrides ALL hardcoded colors across every page.
 * Also injects logo into headers and updates company name everywhere.
 * Include at the BOTTOM of every page body: <script src="branding-loader.js"></script>
 */
(async function () {
  try {
    const res = await fetch('/get_branding');
    if (!res.ok) return;
    const b = await res.json();
    if (!b || (!b.primary_color && !b.accent_color && !b.logo_filename && !b.company_name)) return;

    const primary = b.primary_color || '#1400cc';
    const accent  = b.accent_color  || '#5B21F5';
    const pDark   = shadeColor(primary, -20);
    const pLight  = shadeColor(primary, 20);
    const pRgb    = hexToRgb(primary);
    const aRgb    = hexToRgb(accent);

    // ── 1. Inject override <style> tag ──────────────────────────
    const style = document.createElement('style');
    style.id    = 'serenia-branding-override';
    style.textContent = `
      :root {
        --brand-primary:   ${primary};
        --brand-primary-d: ${pDark};
        --brand-primary-l: ${pLight};
        --brand-accent:    ${accent};
      }

      /* Headers */
      .header {
        background: ${primary} !important;
        box-shadow: 0 4px 20px rgba(${pRgb},0.4) !important;
      }
      .top-bar {
        background: rgba(0,0,0,0.5) !important;
        border-bottom-color: rgba(${pRgb},0.2) !important;
      }

      /* Home page nav buttons */
      .nav-btn {
        background-color: ${accent} !important;
        box-shadow: 0 0 25px rgba(${aRgb},0.45), 0 6px 24px rgba(0,0,0,0.2) !important;
      }
      .nav-btn:hover {
        background-color: ${pLight} !important;
        box-shadow: 0 0 50px rgba(${aRgb},0.75), 0 0 90px rgba(${aRgb},0.35), 0 12px 36px rgba(0,0,0,0.28) !important;
      }

      /* Premium page feature cards */
      .feat-card.dashboard-card {
        background: linear-gradient(135deg, ${primary}, ${accent}) !important;
      }
      .feat-card:hover {
        border-color: rgba(${pRgb},0.4) !important;
      }

      /* Left panels in view pages */
      .left-panel, .panel-bg {
        background: ${primary} !important;
      }

      /* Filter chips active state */
      .fchip.active, .filter-chip.active, .tab.active {
        background: ${primary} !important;
        border-color: ${primary} !important;
      }
      .tab.active {
        color: ${primary} !important;
        background: transparent !important;
        border-bottom-color: ${primary} !important;
      }

      /* Buttons */
      .add-btn-h { color: ${primary} !important; }
      .save-btn, .apply-btn, .btn-save, .gen-btn {
        background: ${primary} !important;
        box-shadow: 0 0 18px rgba(${pRgb},0.35) !important;
      }
      .save-btn:hover, .apply-btn:hover, .btn-save:hover, .gen-btn:hover {
        background: ${pLight} !important;
      }
      .send-btn { background: ${primary} !important; }
      .send-btn:hover { background: ${pLight} !important; }

      /* Stats / KPI accents */
      .sel-count, .donut-center-val { color: ${primary} !important; }
      .sel-chip { background: ${primary} !important; }

      /* Links and highlights */
      .recip-email.has { color: ${primary} !important; }
      .card-title { color: ${primary} !important; }

      /* Kanban dots and deal colors */
      .col-title:first-of-type { color: ${primary} !important; }

      /* Pipeline stage dot */
      .pipe-dot { }

      /* Input focus */
      .field input:focus,
      .field select:focus,
      .field textarea:focus,
      .fsearch:focus,
      .recip-search:focus {
        border-color: ${primary} !important;
      }

      /* Back buttons in headers */
      .back-btn:hover {
        background: rgba(255,255,255,0.25) !important;
      }

      /* Settings page color previews */
      #previewHeader { background: ${primary} !important; }
      #previewBtn1   { background: ${primary} !important; }
      #previewBtn2   { background: ${accent}  !important; }
    `;
    document.head.appendChild(style);

    // ── 2. Update company name everywhere ──────────────────────
    const companyName = b.company_name || 'SERENIA';
    document.querySelectorAll('.brand-name, [data-brand-name]').forEach(el => {
      el.textContent = companyName;
    });
    // Update page title
    if (b.company_name) {
      document.title = document.title.replace(/SERENIA/g, b.company_name);
    }

    // ── 3. Inject logo into headers ────────────────────────────
    if (b.logo_filename) {
      document.querySelectorAll('.header').forEach(header => {
        // Don't add duplicate logos
        if (header.querySelector('.injected-logo')) return;
        const img = document.createElement('img');
        img.src       = `/photos/${encodeURIComponent(b.logo_filename)}`;
        img.alt       = companyName;
        img.className = 'injected-logo';
        img.style.cssText = 'height:34px;width:auto;max-width:120px;object-fit:contain;border-radius:6px;flex-shrink:0;margin-right:4px';
        img.onerror = () => img.style.display = 'none';
        // Insert after back button if present, else prepend
        const backBtn = header.querySelector('.back-btn');
        if (backBtn) {
          backBtn.insertAdjacentElement('afterend', img);
        } else {
          header.insertBefore(img, header.firstChild);
        }
      });
    }

    // ── 4. Also update brand-logo img elements ─────────────────
    if (b.logo_filename) {
      document.querySelectorAll('.brand-logo, [data-brand-logo]').forEach(el => {
        el.src   = `/photos/${encodeURIComponent(b.logo_filename)}`;
        el.style.display = 'block';
      });
    }

  } catch (e) {
    // Silently fail — branding is cosmetic
  }

  function shadeColor(hex, pct) {
    try {
      const n = parseInt(hex.replace('#',''), 16);
      const r = Math.min(255, Math.max(0, (n >> 16) + pct));
      const g = Math.min(255, Math.max(0, ((n >> 8) & 0xff) + pct));
      const b = Math.min(255, Math.max(0, (n & 0xff) + pct));
      return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
    } catch { return hex; }
  }

  function hexToRgb(hex) {
    try {
      const n = parseInt(hex.replace('#',''), 16);
      return `${(n>>16)&255},${(n>>8)&255},${n&255}`;
    } catch { return '20,0,204'; }
  }
})();
