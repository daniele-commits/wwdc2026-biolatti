/* =============================================================================
   COOKIE BANNER — biolatti.it
   ---------------------------------------------------------------------------
   - Conforme Garante Privacy 2021 + EDPB 2023: rifiuto allo stesso livello
     di "Accetta tutto", granularità categorie, no cookie wall.
   - Google Consent Mode v2: GA4 bloccato di default fino al consenso.
   - i18n IT/EN basato su <html lang>.
   - Zero dipendenze esterne. Asset unico, CSS iniettato.
   ========================================================================== */
(function () {
  'use strict';

  // -------------------------------------------------------------------------
  // CONFIG
  // -------------------------------------------------------------------------
  var STORAGE_KEY = 'biolatti_cookie_consent_v1';
  var CONSENT_VERSION = 1;          // bump per forzare ri-consenso a tutti
  var CONSENT_EXPIRY_DAYS = 180;    // 6 mesi (best practice italiana)

  var LANG = (document.documentElement.lang || 'it').toLowerCase().slice(0, 2);
  var I18N = {
    it: {
      title: 'Cookie e privacy',
      body: 'Questo sito usa cookie tecnici per funzionare correttamente e — solo con il tuo consenso — cookie analitici (Google Analytics) per capire come viene utilizzato. Niente profilazione, niente marketing. Puoi cambiare idea in qualsiasi momento dal link in fondo alla pagina.',
      cookiePolicy: 'Cookie policy',
      privacyPolicy: 'Privacy policy',
      acceptAll: 'Accetta tutto',
      rejectAll: 'Rifiuta tutto',
      preferences: 'Preferenze',
      save: 'Salva preferenze',
      close: 'Chiudi',
      modalTitle: 'Le tue preferenze sui cookie',
      modalIntro: 'Scegli quali categorie di cookie autorizzare. La tua scelta verrà conservata per 6 mesi (a meno che tu non svuoti i dati del browser) e potrai modificarla in qualsiasi momento.',
      catTechTitle: 'Cookie tecnici',
      catTechDesc: 'Necessari per il funzionamento del sito (preferenze di navigazione, sessione). Sempre attivi, non richiedono consenso.',
      catAnalyticsTitle: 'Cookie analitici',
      catAnalyticsDesc: 'Google Analytics 4 con IP anonimizzato. Mi aiutano a capire quali contenuti sono utili. Nessun dato è venduto o condiviso per marketing.',
      always: 'Sempre attivi',
      manageLink: 'Gestisci cookie',
      moreInfo: 'Per saperne di più:'
    },
    en: {
      title: 'Cookies and privacy',
      body: 'This site uses technical cookies to work properly and — only with your consent — analytics cookies (Google Analytics) to understand how it is used. No profiling, no marketing. You can change your mind at any time from the link in the footer.',
      cookiePolicy: 'Cookie policy',
      privacyPolicy: 'Privacy policy',
      acceptAll: 'Accept all',
      rejectAll: 'Reject all',
      preferences: 'Preferences',
      save: 'Save preferences',
      close: 'Close',
      modalTitle: 'Your cookie preferences',
      modalIntro: 'Choose which categories of cookies to allow. Your choice will be kept for 6 months (unless you clear your browser data) and you can change it at any time.',
      catTechTitle: 'Technical cookies',
      catTechDesc: 'Required for the site to work (navigation preferences, session). Always active, no consent needed.',
      catAnalyticsTitle: 'Analytics cookies',
      catAnalyticsDesc: 'Google Analytics 4 with anonymised IP. Helps me understand which content is useful. No data is sold or shared for marketing.',
      always: 'Always active',
      manageLink: 'Manage cookies',
      moreInfo: 'Learn more:'
    }
  };
  var t = I18N[LANG] || I18N.it;

  // Path policy con .html esplicito: funziona sia in produzione (Apache
  // normalizza con/senza .html via .htaccess) sia in locale via http.server
  // (che NON gestisce i rewrite di clean URL).
  var COOKIE_POLICY_PATH  = (LANG === 'en') ? '/en/cookie-policy.html'  : '/cookie-policy.html';
  var PRIVACY_POLICY_PATH = (LANG === 'en') ? '/en/privacy-policy.html' : '/privacy-policy.html';

  // -------------------------------------------------------------------------
  // STORAGE HELPERS
  // -------------------------------------------------------------------------
  function readConsent() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (data.v !== CONSENT_VERSION) return null;
      // Check expiry
      var ageDays = (Date.now() - data.ts) / (1000 * 60 * 60 * 24);
      if (ageDays > CONSENT_EXPIRY_DAYS) return null;
      return data;
    } catch (e) { return null; }
  }

  function writeConsent(analytics) {
    var data = {
      v: CONSENT_VERSION,
      ts: Date.now(),
      technical: true,
      analytics: !!analytics
    };
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch (e) {}
    applyConsent(data);
    return data;
  }

  // -------------------------------------------------------------------------
  // CONSENT APPLICATION (Google Consent Mode v2)
  // -------------------------------------------------------------------------
  function applyConsent(data) {
    if (typeof window.gtag !== 'function') {
      // gtag arriverà più tardi: window.dataLayer è il fallback diretto
      window.dataLayer = window.dataLayer || [];
      window.gtag = function(){ window.dataLayer.push(arguments); };
    }
    window.gtag('consent', 'update', {
      'analytics_storage': data.analytics ? 'granted' : 'denied',
      'ad_storage': 'denied',
      'ad_user_data': 'denied',
      'ad_personalization': 'denied'
    });
  }

  // -------------------------------------------------------------------------
  // CSS (iniettato come <style>)
  // -------------------------------------------------------------------------
  var CSS = [
    '.bcb-root *,.bcb-root *::before,.bcb-root *::after{box-sizing:border-box}',
    '.bcb-banner,.bcb-modal-backdrop,.bcb-fab{font-family:"Lato",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#2B2B2B}',
    '.bcb-banner{position:fixed;left:0;right:0;bottom:0;background:#F8F8F6;border-top:4px solid #FFC300;box-shadow:0 -8px 24px rgba(0,0,0,.12);z-index:9999;padding:18px 24px;animation:bcbSlideUp .35s ease-out}',
    '@keyframes bcbSlideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}',
    '.bcb-banner__inner{max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:20px;flex-wrap:wrap}',
    '.bcb-banner__text{flex:1;min-width:280px}',
    '.bcb-banner__title{font-family:"Montserrat",sans-serif;font-weight:800;font-size:15px;margin:0 0 4px;text-transform:uppercase;letter-spacing:.05em;color:#2B2B2B}',
    '.bcb-banner__title::before{content:"";display:inline-block;width:10px;height:10px;border:2px solid #E96D50;border-radius:50%;border-right-color:transparent;margin-right:8px;vertical-align:-1px}',
    '.bcb-banner__body{font-size:14px;line-height:1.55;color:#444;margin:0}',
    '.bcb-banner__body a{color:#00796B;text-decoration:underline;text-underline-offset:2px}',
    '.bcb-banner__actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}',
    '.bcb-btn{font-family:"Montserrat",sans-serif;font-weight:700;font-size:13px;letter-spacing:.02em;padding:10px 18px;border-radius:6px;border:2px solid transparent;cursor:pointer;transition:transform .1s,background-color .2s,border-color .2s,color .2s;white-space:nowrap;line-height:1.2}',
    '.bcb-btn:active{transform:scale(.98)}',
    '.bcb-btn:focus-visible{outline:3px solid #FFC300;outline-offset:2px}',
    '.bcb-btn--primary{background:#FFC300;color:#2B2B2B;border-color:#FFC300}',
    '.bcb-btn--primary:hover,.bcb-btn--primary:focus{background:#e6b000;border-color:#e6b000}',
    '.bcb-btn--secondary{background:#FFFFFF;color:#2B2B2B;border-color:#2B2B2B}',
    '.bcb-btn--secondary:hover,.bcb-btn--secondary:focus{background:#2B2B2B;color:#FFFFFF}',
    '.bcb-btn--ghost{background:transparent;color:#00796B;border-color:transparent;padding:10px 12px;text-decoration:underline;text-underline-offset:3px}',
    '.bcb-btn--ghost:hover,.bcb-btn--ghost:focus{color:#005f55}',
    '.bcb-modal-backdrop{position:fixed;inset:0;background:rgba(43,43,43,.55);z-index:10000;display:flex;align-items:center;justify-content:center;padding:24px;animation:bcbFade .2s ease-out}',
    '@keyframes bcbFade{from{opacity:0}to{opacity:1}}',
    '.bcb-modal{background:#FFFFFF;max-width:560px;width:100%;max-height:90vh;overflow-y:auto;border-radius:10px;border-top:6px solid #FFC300;padding:32px;box-shadow:0 12px 48px rgba(0,0,0,.28)}',
    '.bcb-modal__title{font-family:"Montserrat",sans-serif;font-weight:800;font-size:22px;margin:0 0 12px;color:#2B2B2B}',
    '.bcb-modal__intro{font-size:15px;line-height:1.6;color:#444;margin:0 0 24px}',
    '.bcb-modal__intro a{color:#00796B;text-decoration:underline}',
    '.bcb-cat{padding:18px 0;border-top:1px solid #E0E0E0}',
    '.bcb-cat:last-of-type{border-bottom:1px solid #E0E0E0;margin-bottom:24px}',
    '.bcb-cat__head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:6px}',
    '.bcb-cat__name{font-family:"Montserrat",sans-serif;font-weight:700;font-size:15px;margin:0}',
    '.bcb-cat__desc{font-size:13px;line-height:1.55;color:#555;margin:0}',
    '.bcb-cat__always{font-family:"Montserrat",sans-serif;font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#00796B;background:#E5F2F0;padding:4px 10px;border-radius:4px;flex-shrink:0}',
    '.bcb-switch{position:relative;display:inline-block;width:46px;height:26px;flex-shrink:0}',
    '.bcb-switch input{opacity:0;width:0;height:0}',
    '.bcb-switch__slider{position:absolute;cursor:pointer;inset:0;background:#cfcfcf;transition:.25s;border-radius:26px}',
    '.bcb-switch__slider::before{position:absolute;content:"";height:20px;width:20px;left:3px;top:3px;background:#FFFFFF;transition:.25s;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.2)}',
    '.bcb-switch input:checked + .bcb-switch__slider{background:#FFC300}',
    '.bcb-switch input:checked + .bcb-switch__slider::before{transform:translateX(20px)}',
    '.bcb-switch input:focus-visible + .bcb-switch__slider{outline:3px solid #FFC300;outline-offset:2px}',
    '.bcb-modal__actions{display:flex;flex-wrap:wrap;gap:10px;justify-content:flex-end}',
    '.bcb-fab{position:fixed;left:14px;bottom:14px;width:38px;height:38px;border-radius:50%;background:#2B2B2B;color:#FFC300;border:none;cursor:pointer;z-index:9998;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(0,0,0,.18);transition:transform .15s,background-color .2s;opacity:.55}',
    '.bcb-fab:hover{transform:scale(1.08);background:#FFC300;color:#2B2B2B;opacity:1}',
    '.bcb-fab:focus-visible{outline:3px solid #FFC300;outline-offset:2px;opacity:1}',
    '.bcb-fab svg{width:18px;height:18px}',
    '@media (max-width:680px){.bcb-banner{padding:16px}.bcb-banner__inner{gap:14px}.bcb-banner__actions{width:100%}.bcb-btn{flex:1;min-width:0;padding:10px 12px;font-size:12px}.bcb-modal{padding:24px}.bcb-modal__title{font-size:20px}.bcb-fab{left:10px;bottom:10px;width:34px;height:34px}}',
    '@media (prefers-reduced-motion:reduce){.bcb-banner,.bcb-modal-backdrop{animation:none}.bcb-switch__slider,.bcb-switch__slider::before,.bcb-fab,.bcb-btn{transition:none}}'
  ].join('');

  function injectStyles() {
    var s = document.createElement('style');
    s.id = 'bcb-styles';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  // -------------------------------------------------------------------------
  // DOM BUILDERS
  // -------------------------------------------------------------------------
  function policyLinks() {
    return t.moreInfo +
      ' <a href="' + COOKIE_POLICY_PATH + '">' + t.cookiePolicy + '</a> · ' +
      '<a href="' + PRIVACY_POLICY_PATH + '">' + t.privacyPolicy + '</a>';
  }

  function buildBanner() {
    var html =
      '<div class="bcb-banner__inner">' +
        '<div class="bcb-banner__text">' +
          '<p class="bcb-banner__title">' + t.title + '</p>' +
          '<p class="bcb-banner__body">' + t.body + ' ' + policyLinks() + '</p>' +
        '</div>' +
        '<div class="bcb-banner__actions">' +
          '<button type="button" class="bcb-btn bcb-btn--ghost" data-bcb-action="prefs">' + t.preferences + '</button>' +
          '<button type="button" class="bcb-btn bcb-btn--secondary" data-bcb-action="reject">' + t.rejectAll + '</button>' +
          '<button type="button" class="bcb-btn bcb-btn--primary" data-bcb-action="accept">' + t.acceptAll + '</button>' +
        '</div>' +
      '</div>';
    var el = document.createElement('div');
    el.className = 'bcb-root bcb-banner';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', t.title);
    el.setAttribute('aria-live', 'polite');
    el.innerHTML = html;
    return el;
  }

  function buildModal(current) {
    var analyticsChecked = current && current.analytics ? 'checked' : '';
    var html =
      '<div class="bcb-modal" role="dialog" aria-modal="true" aria-labelledby="bcb-modal-title">' +
        '<h2 class="bcb-modal__title" id="bcb-modal-title">' + t.modalTitle + '</h2>' +
        '<p class="bcb-modal__intro">' + t.modalIntro + ' ' + policyLinks() + '</p>' +
        '<div class="bcb-cat">' +
          '<div class="bcb-cat__head">' +
            '<h3 class="bcb-cat__name">' + t.catTechTitle + '</h3>' +
            '<span class="bcb-cat__always">' + t.always + '</span>' +
          '</div>' +
          '<p class="bcb-cat__desc">' + t.catTechDesc + '</p>' +
        '</div>' +
        '<div class="bcb-cat">' +
          '<div class="bcb-cat__head">' +
            '<h3 class="bcb-cat__name">' + t.catAnalyticsTitle + '</h3>' +
            '<label class="bcb-switch" aria-label="' + t.catAnalyticsTitle + '">' +
              '<input type="checkbox" data-bcb-cat="analytics" ' + analyticsChecked + '>' +
              '<span class="bcb-switch__slider"></span>' +
            '</label>' +
          '</div>' +
          '<p class="bcb-cat__desc">' + t.catAnalyticsDesc + '</p>' +
        '</div>' +
        '<div class="bcb-modal__actions">' +
          '<button type="button" class="bcb-btn bcb-btn--secondary" data-bcb-action="reject">' + t.rejectAll + '</button>' +
          '<button type="button" class="bcb-btn bcb-btn--secondary" data-bcb-action="accept">' + t.acceptAll + '</button>' +
          '<button type="button" class="bcb-btn bcb-btn--primary" data-bcb-action="save">' + t.save + '</button>' +
        '</div>' +
      '</div>';
    var el = document.createElement('div');
    el.className = 'bcb-root bcb-modal-backdrop';
    el.innerHTML = html;
    return el;
  }

  function buildFab() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'bcb-root bcb-fab';
    btn.setAttribute('aria-label', t.manageLink);
    btn.title = t.manageLink;
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<path d="M21 12a9 9 0 1 1-9-9 4 4 0 0 0 4 4 4 4 0 0 0 4 4 4 4 0 0 0 1 1z"/>' +
        '<circle cx="9" cy="10" r="0.8" fill="currentColor"/>' +
        '<circle cx="14" cy="14" r="0.8" fill="currentColor"/>' +
        '<circle cx="10" cy="16" r="0.8" fill="currentColor"/>' +
      '</svg>';
    return btn;
  }

  // -------------------------------------------------------------------------
  // STATE & UI LOGIC
  // -------------------------------------------------------------------------
  var bannerEl = null, modalEl = null, fabEl = null, lastFocus = null;

  function showBanner() {
    if (bannerEl) return;
    bannerEl = buildBanner();
    document.body.appendChild(bannerEl);
    bannerEl.addEventListener('click', onBannerClick);
  }

  function hideBanner() {
    if (bannerEl) { bannerEl.remove(); bannerEl = null; }
  }

  function openModal() {
    if (modalEl) return;
    var current = readConsent();
    modalEl = buildModal(current);
    document.body.appendChild(modalEl);
    lastFocus = document.activeElement;
    modalEl.addEventListener('click', onModalClick);
    document.addEventListener('keydown', onKeyDown);
    // focus primo bottone azione
    setTimeout(function () {
      var first = modalEl.querySelector('[data-bcb-action="save"]');
      if (first) first.focus();
    }, 30);
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.remove();
    modalEl = null;
    document.removeEventListener('keydown', onKeyDown);
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  function showFab() {
    if (fabEl) return;
    fabEl = buildFab();
    fabEl.addEventListener('click', openModal);
    document.body.appendChild(fabEl);
  }

  function onBannerClick(e) {
    var t = e.target.closest('[data-bcb-action]');
    if (!t) return;
    var action = t.getAttribute('data-bcb-action');
    if (action === 'accept') { writeConsent(true); hideBanner(); showFab(); }
    else if (action === 'reject') { writeConsent(false); hideBanner(); showFab(); }
    else if (action === 'prefs') { openModal(); }
  }

  function onModalClick(e) {
    if (e.target === modalEl) { closeModal(); return; }
    var t = e.target.closest('[data-bcb-action]');
    if (!t) return;
    var action = t.getAttribute('data-bcb-action');
    if (action === 'accept') {
      writeConsent(true); closeModal(); hideBanner(); showFab();
    } else if (action === 'reject') {
      writeConsent(false); closeModal(); hideBanner(); showFab();
    } else if (action === 'save') {
      var cb = modalEl.querySelector('[data-bcb-cat="analytics"]');
      writeConsent(cb && cb.checked); closeModal(); hideBanner(); showFab();
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Escape' && modalEl) closeModal();
  }

  // -------------------------------------------------------------------------
  // PUBLIC API
  // -------------------------------------------------------------------------
  window.BiolattiCookieBanner = {
    open: openModal,
    reset: function () {
      try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
      location.reload();
    }
  };

  // Aggancio trigger esistenti nel footer/pagina che usano data-cookie-settings
  // o link con href="#cookie-settings"
  function hookExistingTriggers() {
    document.querySelectorAll('[data-cookie-settings], a[href="#cookie-settings"], a[href="#manage-cookies"]')
      .forEach(function (el) {
        el.addEventListener('click', function (ev) {
          ev.preventDefault();
          openModal();
        });
      });
  }

  // -------------------------------------------------------------------------
  // BOOT
  // -------------------------------------------------------------------------
  function boot() {
    injectStyles();
    hookExistingTriggers();
    var saved = readConsent();
    if (saved) {
      applyConsent(saved);
      showFab();
    } else {
      showBanner();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
