// Google I/O 2026 — Biolatti.it special section
// Minimal JS: tag filter, auto-update relative timestamps

(function () {
  'use strict';

  // -----------------------------
  // Tag filter on index page
  // -----------------------------
  const tags = document.querySelectorAll('[data-tag-filter]');
  const cards = document.querySelectorAll('[data-tag]');

  if (tags.length && cards.length) {
    tags.forEach(function (tag) {
      tag.addEventListener('click', function (e) {
        e.preventDefault();
        const filter = tag.getAttribute('data-tag-filter');
        tags.forEach(function (t) { t.classList.remove('active'); });
        tag.classList.add('active');
        cards.forEach(function (card) {
          const cardTags = (card.getAttribute('data-tag') || '').split(',').map(function (s) { return s.trim(); });
          if (filter === 'all' || cardTags.indexOf(filter) !== -1) {
            card.style.display = '';
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  // -----------------------------
  // Relative timestamps (data-ts attribute = ISO 8601)
  // -----------------------------
  const timestamps = document.querySelectorAll('[data-ts]');
  const lang = document.documentElement.lang || 'it';

  function relativeTime(iso) {
    const then = new Date(iso);
    const now = new Date();
    const diffSec = Math.floor((now - then) / 1000);
    const labels = lang === 'en'
      ? { now: 'just now', m: 'min ago', h: 'h ago', d: 'd ago' }
      : { now: 'adesso', m: ' min fa', h: ' h fa', d: ' g fa' };
    if (diffSec < 60) return labels.now;
    if (diffSec < 3600) return Math.floor(diffSec / 60) + labels.m;
    if (diffSec < 86400) return Math.floor(diffSec / 3600) + labels.h;
    return Math.floor(diffSec / 86400) + labels.d;
  }

  timestamps.forEach(function (el) {
    el.textContent = relativeTime(el.getAttribute('data-ts'));
  });
})();
