(() => {
  'use strict';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const hero = document.querySelector('.hero');
  let pointerFrame = 0, latest = null, scrollFrame = 0;
  document.addEventListener('pointermove', event => {
    if (reduced.matches || event.pointerType === 'touch') return;
    latest = { x: event.clientX, y: event.clientY, target: event.target };
    if (pointerFrame) return;
    pointerFrame = requestAnimationFrame(() => {
      pointerFrame = 0;
      const card = latest.target.closest?.('.card');
      if (card) {
        const r = card.getBoundingClientRect();
        card.style.setProperty('--card-x', ((latest.x - r.left) / r.width * 100).toFixed(1) + '%');
        card.style.setProperty('--card-y', ((latest.y - r.top) / r.height * 100).toFixed(1) + '%');
      }
      if (hero?.contains(latest.target)) {
        const r = hero.getBoundingClientRect();
        hero.style.setProperty('--light-x', (60 + latest.x / r.width * 25).toFixed(1) + '%');
        hero.style.setProperty('--light-y', (20 + (latest.y - r.top) / r.height * 35).toFixed(1) + '%');
      }
    });
  }, { passive: true });
  const updateProgress = () => {
    scrollFrame = 0;
    const limit = document.documentElement.scrollHeight - innerHeight;
    document.documentElement.style.setProperty('--reading', String(limit > 0 ? Math.max(0, Math.min(1, scrollY / limit)) : 0));
  };
  const queue = () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(updateProgress); };
  document.addEventListener('scroll', queue, { passive: true });
  window.addEventListener('resize', queue, { passive: true });
  document.querySelectorAll('[data-tab], #filters-details').forEach(el => el.addEventListener('click', queue));
  updateProgress();
})();
