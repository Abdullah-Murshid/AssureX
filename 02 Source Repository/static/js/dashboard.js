/* Presentation-only enhancements; existing forms and requests retain their behaviour. */
(() => {
  const body = document.body;
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.querySelector('.sidebar-backdrop');
  const mobile = window.matchMedia('(max-width: 760px)');
  if (toggle && sidebar) {
    try {
      const isCol = localStorage.getItem('assurex.sidebar') === 'collapsed';
      body.classList.toggle('sidebar-collapsed', isCol);
      document.documentElement.classList.toggle('sidebar-collapsed', isCol);
    } catch {}
    requestAnimationFrame(() => {
      setTimeout(() => {
        document.documentElement.classList.remove('no-sidebar-transition');
      }, 50);
    });
    const sync = () => {
      const open = mobile.matches ? body.classList.contains('sidebar-open') : !body.classList.contains('sidebar-collapsed');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Collapse navigation' : 'Expand navigation');
      backdrop.hidden = !(mobile.matches && open);
      sidebar.inert = mobile.matches && !open;
    };
    const close = () => { body.classList.remove('sidebar-open'); sync(); toggle.focus(); };
    toggle.addEventListener('click', () => {
      document.documentElement.classList.remove('no-sidebar-transition');
      if (mobile.matches) body.classList.toggle('sidebar-open');
      else {
        body.classList.toggle('sidebar-collapsed');
        document.documentElement.classList.toggle('sidebar-collapsed', body.classList.contains('sidebar-collapsed'));
        try { localStorage.setItem('assurex.sidebar', body.classList.contains('sidebar-collapsed') ? 'collapsed' : 'expanded'); } catch {}
      }
      sync();
      if (mobile.matches && body.classList.contains('sidebar-open')) sidebar.querySelector('a').focus();
    });
    backdrop.addEventListener('click', close);
    document.addEventListener('keydown', event => {
      if (!mobile.matches || !body.classList.contains('sidebar-open')) return;
      if (event.key === 'Escape') close();
      if (event.key === 'Tab') {
        const items = [...sidebar.querySelectorAll('a,button'), toggle];
        const first = items[0], last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    mobile.addEventListener('change', () => { body.classList.remove('sidebar-open'); sync(); });
    sync();
  }
  document.querySelectorAll('.data-table').forEach(table => {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-scroll';
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    wrapper.setAttribute('aria-label', (table.closest('.panel')?.querySelector('.panel-title')?.textContent.trim() || 'Data') + ' table');
    table.before(wrapper);
    wrapper.append(table);
  });
  document.querySelectorAll('label').forEach((label, index) => {
    if (label.htmlFor || label.querySelector('input,select,textarea')) return;
    const control = label.parentElement.querySelector('input:not([type=hidden]),select,textarea');
    if (control) { if (!control.id) control.id = 'field-' + index; label.htmlFor = control.id; }
  });
  document.querySelectorAll('[style]').forEach(element => {
    if (element.style.display === 'grid' && element.style.gridTemplateColumns.includes('1fr 1fr')) element.classList.add('responsive-columns');
    if (element.style.display === 'flex') element.classList.add('responsive-actions');
  });
  const drop = document.getElementById('dropZone');
  if (drop) {
    drop.tabIndex = 0;
    drop.setAttribute('role', 'button');
    drop.setAttribute('aria-label', 'Choose CSV file');
    drop.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); document.getElementById('fileInput').click(); }
    });
  }

  /* Theme Switcher */
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    const isDark = () => document.documentElement.classList.contains('dark-theme');
    themeToggle.addEventListener('click', () => {
      const next = !isDark();
      document.documentElement.classList.toggle('dark-theme', next);
      document.body.classList.toggle('dark-theme', next);
      try { localStorage.setItem('assurex.theme', next ? 'dark' : 'light'); } catch {}
      themeToggle.setAttribute('aria-label', next ? 'Switch to light theme' : 'Switch to dark theme');
      themeToggle.setAttribute('title', next ? 'Switch to light theme' : 'Switch to dark theme');
    });
  }

  /* Copy to Clipboard (Hash) */
  document.querySelectorAll('.copy-hash-btn, [data-copy]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      const text = btn.getAttribute('data-copy') || btn.innerText;
      try {
        await navigator.clipboard.writeText(text);
        const original = btn.innerHTML;
        btn.innerHTML = '✓ Copied!';
        btn.style.color = '#10b981';
        setTimeout(() => { btn.innerHTML = original; btn.style.color = ''; }, 2000);
      } catch (err) {
        console.error('Copy failed', err);
      }
    });
  });

  /* Segmented View Switchers */
  document.querySelectorAll('[data-view-target]').forEach(tab => {
    tab.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = tab.getAttribute('data-view-target');
      const container = tab.closest('.panel') || tab.closest('.main-content') || document.body;
      const group = tab.getAttribute('data-view-group') || 'default';
      container.querySelectorAll(`[data-view-group="${group}"]`).forEach(btn => btn.classList.remove('active'));
      tab.classList.add('active');
      container.querySelectorAll(`[data-view-pane="${group}"]`).forEach(pane => {
        pane.hidden = (pane.id !== targetId);
      });
    });
  });

  /* Image Lightbox for Summary Card and Evidence */
  const setupLightbox = () => {
    let lb = document.getElementById('app-lightbox');
    if (!lb) {
      lb = document.createElement('div');
      lb.id = 'app-lightbox';
      lb.className = 'image-lightbox';
      lb.innerHTML = '<div class="lightbox-content"><div style="text-align:right;width:100%;margin-bottom:8px;"><span class="lightbox-close" role="button" tabindex="0" aria-label="Close image">✕</span></div><img class="lightbox-img" src="" alt="Enlarged view"></div>';
      document.body.appendChild(lb);
      const closeBtn = lb.querySelector('.lightbox-close');
      if (closeBtn) closeBtn.addEventListener('click', () => lb.classList.remove('active'));
      lb.addEventListener('click', (e) => { if (e.target === lb) lb.classList.remove('active'); });
      document.addEventListener('keydown', (e) => { if (e.key === 'Escape') lb.classList.remove('active'); });
    }
    document.querySelectorAll('.summary-card-img, .lightbox-trigger').forEach(img => {
      img.style.cursor = 'zoom-in';
      img.addEventListener('click', () => {
        const modalImg = lb.querySelector('.lightbox-img');
        if (modalImg) {
          modalImg.src = img.src || img.getAttribute('data-src');
          lb.classList.add('active');
        }
      });
    });
  };
  setupLightbox();

  /* Live File Upload Previews */
  document.querySelectorAll('input[type="file"]').forEach(input => {
    if (input.id === 'fileInput') return;
    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) return;
      let prev = input.parentElement.querySelector('.dropzone-preview-card');
      if (!prev) {
        prev = document.createElement('div');
        prev.className = 'dropzone-preview-card';
        input.parentElement.appendChild(prev);
      }
      const isImg = file.type.startsWith('image/');
      const sizeKB = (file.size / 1024).toFixed(1);
      if (isImg) {
        const url = URL.createObjectURL(file);
        prev.innerHTML = `<img src="${url}" class="dropzone-thumb" alt="Preview"><div><strong style="font-size:12px;">${file.name}</strong><br><small style="color:var(--text-muted);font-size:11px;">${sizeKB} KB · Ready for upload</small></div>`;
      } else {
        prev.innerHTML = `<div><strong style="color:var(--primary);font-size:12px;">📄 ${file.name}</strong><br><small style="color:var(--text-muted);font-size:11px;">${sizeKB} KB · Document ready</small></div>`;
      }
    });
  });
})();
