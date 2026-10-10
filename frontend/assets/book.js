// Book behaviour: contents drawer, arrow-key page turning, and remembering
// visited pages (per browser) for the contents page.
(() => {
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage blocked */ } },
  };
  const page = document.body.dataset.page;

  if (page && page !== 'index') {
    const seen = store.get('sdb.seen', []);
    if (!seen.includes(page)) { seen.push(page); store.set('sdb.seen', seen); }
    store.set('sdb.last', location.pathname.split('/').slice(-3).join('/'));
  }

  // Contents drawer
  const btn = document.querySelector('.bk-toc-btn'), drawer = document.getElementById('bk-drawer');
  if (btn && drawer) {
    const open = v => {
      drawer.hidden = !v; btn.setAttribute('aria-expanded', v);
      if (v) (drawer.querySelector('[aria-current="page"]') || drawer.querySelector('a')).focus();
      else btn.focus();
    };
    btn.addEventListener('click', () => open(true));
    drawer.querySelector('.bk-close').addEventListener('click', () => open(false));
    drawer.addEventListener('click', e => { if (e.target === drawer) open(false); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !drawer.hidden) open(false); });
  }

  // Arrow keys turn pages, unless the reader is using a control on the page
  document.addEventListener('keydown', e => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.target.closest('input, select, textarea, button, [contenteditable]')) return;
    if (drawer && !drawer.hidden) return;
    const dir = e.key === 'ArrowRight' ? 'next' : e.key === 'ArrowLeft' ? 'prev' : null;
    const link = dir && document.querySelector(`[data-nav="${dir}"]`);
    if (link) location.href = link.href;
  });

  // Contents page: mark visited pages and offer "continue"
  if (page === 'index') {
    const seen = store.get('sdb.seen', []);
    document.querySelectorAll('.ix-topic a[data-page]').forEach(a => a.classList.toggle('seen', seen.includes(a.dataset.page)));
    const last = store.get('sdb.last', null), cont = document.getElementById('ix-continue');
    if (last && cont && document.querySelector(`a[href="${last}"]`)) { cont.href = last; cont.hidden = false; }
  }
})();
