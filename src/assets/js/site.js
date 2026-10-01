/* Ranko — site script. Small, no dependencies (uses Lenis only if present). */
(() => {
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];

  /* ---------- smooth scroll (Lenis, optional) */
  let lenis = null;
  if (window.Lenis && !RM) {
    lenis = new Lenis({ lerp: 0.1, anchors: true });
    const raf = (t) => { lenis.raf(t); requestAnimationFrame(raf); };
    requestAnimationFrame(raf);
  }

  /* ---------- home intro: remove the curtain once it has lifted */
  const intro = $('.intro');
  if (intro) {
    if (document.documentElement.classList.contains('intro-on')) setTimeout(() => intro.remove(), 2200);
    else intro.remove();
  }

  /* ---------- home project wall: load and decode the pictures while the page is at rest after opening,
     so they don't all have to be decoded at once when the visitor scrolls past the showreel */
  const wallImgs = $$('.k-cards img');
  if (wallImgs.length) {
    const warm = () => wallImgs.forEach((img, i) => setTimeout(() => {
      img.loading = 'eager';
      img.decode?.().catch(() => {});
    }, i * 120));
    const idle = () => (window.requestIdleCallback ? requestIdleCallback(warm, { timeout: 2500 }) : setTimeout(warm, 1200));
    document.readyState === 'complete' ? idle() : addEventListener('load', idle, { once: true });
  }

  /* ---------- project walls (home, Afterhours): widths of the columns so that they all end at the same height, on every
     screen. Each picture keeps its shape (height = ratio × width); the text under them keeps its size, so it is measured. */
  $$('.k-cards').forEach((wall) => {
    const fit = () => {
      const cols = $$('.k-col', wall);
      if (innerWidth < 768 || cols.length < 2) { cols.forEach((c) => { c.style.flex = ''; }); return; }
      const gap = parseFloat(getComputedStyle(wall).columnGap) || 0;
      const W = wall.clientWidth - gap * (cols.length - 1);
      for (let pass = 0; pass < 2; pass++) {   // text may wrap differently once widths change: settle in two passes
        const info = cols.map((c) => {
          const cards = $$('.k-card', c);
          const g = parseFloat(getComputedStyle($('ol', c)).rowGap) || 0;
          const extra = cards.reduce((t, k) => t + k.offsetHeight - $('.media', k).offsetHeight, 0);
          const r = cards.reduce((t, k) => { const m = $('.media', k); return t + (m && m.offsetWidth ? m.offsetHeight / m.offsetWidth : 1); }, 0);
          return { r, fixed: extra + g * (cards.length - 1) };
        });
        const k = info.reduce((t, x) => t + 1 / x.r, 0);
        const H = (W + info.reduce((t, x) => t + x.fixed / x.r, 0)) / k;
        cols.forEach((c, i) => { c.style.flex = `0 0 ${Math.max(0, (H - info[i].fixed) / info[i].r)}px`; });
      }
    };
    fit();
    let t = 0;
    addEventListener('resize', () => { clearTimeout(t); t = setTimeout(fit, 120); });
    document.fonts?.ready.then(fit);
    addEventListener('load', fit, { once: true });
  });

  /* ---------- pill buttons and menu links: on hover each letter rolls down, a copy comes in from the top (cascade) */
  $$('.kn-cta, .k-pill, .kn-nav a').forEach((b) => {
    const text = b.textContent.trim();
    // letters inside <em> (e.g. "Ranko") stay in italics once split
    const it = [];
    const walk = (n, em) => n.childNodes.forEach((c) => (c.nodeType === 3 ? [...c.textContent].forEach(() => it.push(em)) : walk(c, em || c.nodeName === 'EM')));
    walk(b, false);
    const lead = b.textContent.length - b.textContent.trimStart().length;
    b.setAttribute('aria-label', text);
    b.textContent = '';
    const row = document.createElement('span'); row.className = 'roll'; row.setAttribute('aria-hidden', 'true');
    [...text].forEach((ch, i) => {
      const l = document.createElement('span'); l.className = 'roll-l' + (it[i + lead] ? ' is-em' : ''); l.style.setProperty('--i', i);
      const a = document.createElement('span'); a.textContent = ch === ' ' ? '\u00a0' : ch;
      l.append(a, a.cloneNode(true));
      row.append(l);
    });
    b.append(row);
    // pill buttons end with a small "+" (drawn in CSS): turns right on hover, back to the left on leave
    if (b.classList.contains('k-pill')) b.append(Object.assign(document.createElement('i'), { className: 'k-plus' }));
  });

  /* ---------- Montreal clock */
  const clock = $('[data-clock]');
  if (clock) {
    const f = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });   // 24-hour clock
    // hours and minutes, the colon blinks with the seconds (CSS), started on the second
    const tick = () => {
      const p = Object.fromEntries(f.formatToParts(new Date()).map((x) => [x.type, x.value]));
      clock.innerHTML = `${p.hour}<span class="clock-sep">:</span>${p.minute}`;
      clock.firstElementChild.style.animationDelay = `-${Date.now() % 1000}ms`;
    };
    tick(); setInterval(tick, 20000);
  }

  /* ---------- cookies: Google Analytics loads only after "Accept"; the choice can be changed from the footer */
  const box = $('.consent');
  if (box) {
    const id = box.dataset.ga, KEY = 'ranko-consent';
    const get = () => { try { return localStorage.getItem(KEY); } catch (e) { return null; } };
    const save = (v) => { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode: ask again next time */ } };
    const loadGA = () => {
      if (window.gtag) return;
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { dataLayer.push(arguments); };
      gtag('js', new Date()); gtag('config', id);
      const s = document.createElement('script'); s.async = true; s.src = `https://www.googletagmanager.com/gtag/js?id=${id}`;
      document.head.append(s);
    };
    const dropGA = () => document.cookie.split(';').map((c) => c.split('=')[0].trim()).filter((n) => n.startsWith('_ga'))
      .forEach((n) => ['', location.hostname, '.' + location.hostname.replace(/^www\./, '')].forEach((d) => {
        document.cookie = `${n}=; Max-Age=0; path=/${d ? '; domain=' + d : ''}`;
      }));
    const show = (on) => { box.hidden = !on; };
    const choice = get();
    if (choice === 'yes') loadGA(); else if (choice !== 'no') show(true);
    $('[data-consent="yes"]', box).addEventListener('click', () => { save('yes'); show(false); loadGA(); });
    $('[data-consent="no"]', box).addEventListener('click', () => {
      const had = get() === 'yes'; save('no'); show(false);
      if (had) { dropGA(); location.reload(); }   // stop analytics right away
    });
    $$('[data-consent-open]').forEach((b) => b.addEventListener('click', () => show(true)));
  }

  /* ---------- main menu pill: the white pill sits on the current page and glides to the link under the mouse */
  const pill = $('.pill');
  if (pill) {
    const ind = $('.pill-ind', pill), links = $$('a', pill);
    const here = links.find((a) => a.hasAttribute('aria-current')) || null;
    const put = (a) => {
      links.forEach((l) => l.classList.toggle('is-on', l === a));
      if (!a) { ind.style.opacity = 0; return; }
      ind.style.opacity = 1; ind.style.width = `${a.offsetWidth}px`;
      ind.style.transform = `translateX(${a.parentElement.offsetLeft}px)`;
    };
    links.forEach((a) => { a.addEventListener('mouseenter', () => put(a)); a.addEventListener('focus', () => put(a)); });
    pill.addEventListener('mouseleave', () => put(here));
    pill.addEventListener('focusout', (e) => { if (!pill.contains(e.relatedTarget)) put(here); });
    put(here);
    requestAnimationFrame(() => pill.classList.add('is-ready'));
    document.fonts?.ready.then(() => put(here));
  }

  /* ---------- mobile menu */
  const btn = $('.hd-menu'), menu = $('#menu');
  if (btn && menu) {
    const set = (open) => {
      menu.hidden = !open; btn.setAttribute('aria-expanded', open);
      if (!btn.classList.contains('kn-plus')) btn.textContent = open ? 'Close' : 'Menu';   // the '+' button turns into an × in CSS
      document.body.classList.toggle('menu-open', open);
      open ? lenis?.stop() : lenis?.start();
    };
    btn.addEventListener('click', () => set(menu.hidden));
    addEventListener('keydown', (e) => { if (e.key === 'Escape' && !menu.hidden) set(false); });
    $$('a', menu).forEach((a) => a.addEventListener('click', () => set(false)));
  }

  /* ---------- big titles: pull the first letter onto the text edge (large letters carry a built-in side space) */
  const ctx = document.createElement('canvas').getContext('2d');
  /* page headers: when the title leaves no room on its right, the sentence goes under it, still on the right (class is-stacked) */
  const stack = () => $$('.k-hero').forEach((hd) => {
    const t = $('h1', hd), p = $('.page-intro', hd);
    if (!t || !p) return;
    hd.classList.remove('is-stacked');
    if (p.getBoundingClientRect().top >= t.getBoundingClientRect().bottom - 1) hd.classList.add('is-stacked');
  });
  stack(); addEventListener('resize', stack); document.fonts?.ready.then(stack);

  const align = () => $$('.page-t, .pj-t, .big-t, .mid-t, .page-intro, .next-t, .sec-t').forEach((el) => {
    if (getComputedStyle(el).textAlign === 'right') { el.style.marginLeft = ''; return; }   // right-aligned sentences: nothing to nudge on the left
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, { acceptNode: (n) => n.textContent.trim() ? 1 : 3 });
    const node = walker.nextNode();
    if (!node) return;
    const cs = getComputedStyle(node.parentElement);
    ctx.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    const bearing = -ctx.measureText(node.textContent.trim()[0]).actualBoundingBoxLeft;   // space before the ink
    el.style.marginLeft = bearing > 0 ? `${(-bearing / parseFloat(getComputedStyle(el).fontSize)).toFixed(4)}em` : '';
  });
  align();
  document.fonts?.ready.then(align);
  addEventListener('resize', align);

  /* ---------- split big sentences into words (data-split="chars": letter by letter, each word stays one block) */
  $$('[data-split]').forEach((el) => {
    let i = 0;
    const chars = el.dataset.split === 'chars';
    const wrap = (node) => {
      [...node.childNodes].forEach((n) => {
        if (n.nodeType === 3) {
          const frag = document.createDocumentFragment();
          // non-breaking spaces (U+00A0) do not split: words joined by them stay together on one line
          n.textContent.split(/([^\S\u00a0]+)/).forEach((part) => {
            if (!part) return;
            if (/^[^\S\u00a0]+$/.test(part)) { frag.append(' '); return; }
            const w = document.createElement('span'); w.className = 'w';
            for (const piece of chars ? [...part] : [part]) {
              const s = document.createElement('span'); s.textContent = piece; s.style.setProperty('--i', i++);
              w.append(s);
            }
            frag.append(w);
          });
          n.replaceWith(frag);
        } else if (n.nodeType === 1) wrap(n);
      });
    };
    wrap(el);
  });

  /* ---------- reveal on scroll + count-up */
  const count = (el) => {
    const end = parseFloat(el.dataset.count), t0 = performance.now(), d = 1400;
    const step = (t) => {
      const p = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(end * e);
      if (p < 1) requestAnimationFrame(step);
    };
    if (RM) return;
    el.textContent = '0'; requestAnimationFrame(step);
  };
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-in');
      $$('[data-count]', e.target).forEach(count);
      io.unobserve(e.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
  $$('[data-reveal], [data-split]').forEach((el) => {
    // already on screen when the page opens: show right away
    if (el.getBoundingClientRect().top < innerHeight) { el.classList.add('is-in'); $$('[data-count]', el).forEach(count); }
    else io.observe(el);
  });

  /* ---------- Vimeo: loaded only when needed */
  const src = (fig, film) => {
    const q = new URLSearchParams({ dnt: 1 });
    if (fig.dataset.h) q.set('h', fig.dataset.h);
    if (film) { q.set('autoplay', 1); q.set('title', 0); q.set('byline', 0); q.set('portrait', 0); q.set('color', 'fcfcf7'); }
    else { q.set('background', 1); }
    return `https://player.vimeo.com/video/${fig.dataset.vimeo}?${q}`;
  };
  const mount = (fig, film) => {
    if (fig.iframe) return;
    const f = document.createElement('iframe');
    f.src = src(fig, film);
    f.allow = 'autoplay; fullscreen; picture-in-picture';
    f.title = 'Vimeo video'; f.setAttribute('allowfullscreen', '');
    f.addEventListener('load', () => {
      fig.classList.add('is-ready');
      if (!film && fig.dataset.seen !== '1') setTimeout(() => cmd(fig, 'pause'), 300);   // loaded ahead while off screen: wait
    }, { once: true });
    fig.iframe = f; fig.append(f);
    if (film) fig.classList.add('is-playing');
  };
  const cmd = (fig, method) => fig.iframe?.contentWindow?.postMessage(JSON.stringify({ method }), 'https://player.vimeo.com');

  const loops = $$('.vm-loop');
  if (RM) {
    $$('.clip-v:not(.tile-clip)').forEach((v) => { v.src = v.dataset.src; v.style.cursor = 'pointer'; v.addEventListener('click', () => (v.paused ? v.play() : v.pause())); });   // still first, a click plays it (no browser controls bar); tiles keep their still image
    // no autoplaying loops: offer a play button instead
    loops.forEach((fig) => {
      if (fig.classList.contains('tile-vm')) return;   // tiles keep their still image
      const b = document.createElement('button');
      b.className = 'play'; b.type = 'button'; b.innerHTML = '<span>Play</span>';
      b.addEventListener('click', () => { mount(fig, false); b.remove(); });
      fig.append(b);
    });
  } else {
    // Loops start once the visitor interacts (scroll, touch, mouse, key), and only when on screen:
    // the page itself stays light and fast to open.
    const vio = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        const fig = e.target;
        fig.dataset.seen = e.isIntersecting ? '1' : '0';
        if (e.isIntersecting) { fig.iframe ? cmd(fig, 'play') : mount(fig, false); }
        else if (fig.iframe) cmd(fig, 'pause');
      });
    }, { rootMargin: '200px 0px' });
    // hosted clips (MP4): same rule
    const clips = $$('.clip-v');
    const cio = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        const v = e.target;
        if (e.isIntersecting) { if (!v.src) v.src = v.dataset.src; v.play().catch(() => {}); }
        else v.pause();
      });
    }, { rootMargin: '200px 0px' });
    // Videos start while the page is at rest just after it has opened (or at the first mouse move / key):
    // never at the first scroll, which made the page stutter while the Vimeo player loaded.
    const wake = ['pointermove', 'keydown'];
    let started = false;
    const start = () => {
      if (started) return; started = true;
      wake.forEach((t) => removeEventListener(t, start));
      loops.forEach((fig) => vio.observe(fig));
      clips.forEach((v) => cio.observe(v));
      // project tiles with a video: get their player ready now, one by one while the page is at rest,
      // so none has to load during the scroll (that made the page stutter under the showreel)
      // (big screens with a good connection only: on phones or a slow / data-saving connection, each video loads
      // only when it comes near the screen, so the page doesn't download tens of MB for videos never seen)
      const net = navigator.connection || {};
      const rich = innerWidth >= 900 && !net.saveData && !/(^|-)2g|3g/.test(net.effectiveType || '');
      const ahead = rich ? loops.filter((fig) => fig.classList.contains('tile-vm')) : [];
      const next = () => {
        const fig = ahead.shift();
        if (!fig) return;
        if (!fig.iframe) mount(fig, false);
        window.requestIdleCallback ? requestIdleCallback(next, { timeout: 2000 }) : setTimeout(next, 600);
      };
      window.requestIdleCallback ? requestIdleCallback(next, { timeout: 2000 }) : setTimeout(next, 600);
    };
    if (loops.length || clips.length) {
      wake.forEach((t) => addEventListener(t, start, { passive: true }));
      const later = () => (window.requestIdleCallback ? requestIdleCallback(start, { timeout: 1500 }) : setTimeout(start, 800));
      document.readyState === 'complete' ? later() : addEventListener('load', later, { once: true });
    }
  }
  $$('.vm-film').forEach((fig) => {
    $('.play', fig)?.addEventListener('click', () => mount(fig, true));
  });

  /* ---------- home: testimonials take turns (every 6 s, paused while the mouse is on them); the dots choose one */
  const qBox = $('.ai-quote');
  if (qBox) {
    const qs = $$('.ai-q', qBox), dots = $$('.ai-dot', qBox);
    let at = 0, hold = false;
    const show = (k) => {
      qs[at].hidden = true; qs[at].classList.remove('is-on'); dots[at]?.setAttribute('aria-pressed', 'false');
      at = (k + qs.length) % qs.length;
      qs[at].hidden = false; qs[at].classList.add('is-on'); dots[at]?.setAttribute('aria-pressed', 'true');
    };
    dots.forEach((d, k) => d.addEventListener('click', () => show(k)));
    qBox.addEventListener('pointerenter', () => { hold = true; });
    qBox.addEventListener('pointerleave', () => { hold = false; });
    qBox.addEventListener('focusin', () => { hold = true; });
    qBox.addEventListener('focusout', () => { hold = false; });
    if (qs.length > 1 && !RM) setInterval(() => { if (!hold && !document.hidden) show(at + 1); }, 6000);
  }

  /* ---------- Afterhours: a click on a piece of the mosaic opens it full screen */
  const lb = $('.lb');
  if (lb) {
    const btns = $$('.ah-open'), n = btns.length;
    const stage = $('.lb-stage', lb), box = $('.lb-media', lb);
    /* full-screen viewer */
    let idx = 0, opener = null;
    const ratio = (b) => { const [w, h] = b.dataset.ar.split('/').map(Number); return w / h; };
    const vsrc = (b) => {
      const q = new URLSearchParams({ dnt: 1, autoplay: 1, title: 0, byline: 0, portrait: 0, color: 'fcfcf7' });
      if (b.dataset.h) q.set('h', b.dataset.h);
      if (b.dataset.kind === 'loop') { q.set('loop', 1); q.set('muted', 1); }
      return `https://player.vimeo.com/video/${b.dataset.vimeo}?${q}`;
    };
    const fill = () => {
      const b = btns[idx], ar = ratio(b);
      const sw = stage.clientWidth, sh = stage.clientHeight;
      const w = Math.min(sw, sh * ar);
      box.style.width = `${w}px`; box.style.height = `${w / ar}px`;
      const img = $('img', b);
      box.innerHTML = '';
      const pic = new Image(); pic.alt = b.dataset.alt || ''; pic.src = b.dataset.kind === 'image' ? b.dataset.src : img.currentSrc || img.src;
      box.append(pic);
      if (b.dataset.kind !== 'image') {
        const f = document.createElement('iframe');
        f.src = vsrc(b); f.allow = 'autoplay; fullscreen; picture-in-picture'; f.title = b.dataset.title; f.allowFullscreen = true;
        box.append(f);
      }
      $('.lb-title', lb).textContent = b.dataset.title;
      $('.lb-count', lb).textContent = `${idx + 1} / ${n}`;
    };
    const open = (i, from) => {
      idx = i; opener = btns[i]; lb.showModal(); fill(); lenis?.stop();
      if (RM) return;
      const a = from.getBoundingClientRect(), z = box.getBoundingClientRect();
      box.animate([
        { transform: `translate(${a.left - z.left}px, ${a.top - z.top}px) scale(${a.width / z.width})`, transformOrigin: '0 0' },
        { transform: 'none', transformOrigin: '0 0' }], { duration: 700, easing: 'cubic-bezier(.65, 0, .25, 1)' });
      lb.animate([{ backgroundColor: 'rgba(11,11,11,0)' }, { backgroundColor: 'rgba(11,11,11,.97)' }], { duration: 450, easing: 'ease-out' });
    };
    const go = (s) => { idx = (idx + s + n) % n; fill(); };
    btns.forEach((b, k) => b.addEventListener('click', () => open(k, $('.media', b))));
    const shut = () => { box.innerHTML = ''; if (lb.open) lb.close(); lenis?.start(); opener?.focus({ preventScroll: true }); };   // emptying the box stops the video
    $('.lb-close', lb).addEventListener('click', shut);
    $('.lb-prev', lb).addEventListener('click', () => go(-1));
    $('.lb-next', lb).addEventListener('click', () => go(1));
    lb.addEventListener('click', (e) => { if (e.target === lb || e.target === stage) shut(); });
    lb.addEventListener('keydown', (e) => { if (e.key === 'ArrowLeft') go(-1); if (e.key === 'ArrowRight') go(1); });
    lb.addEventListener('cancel', (e) => { e.preventDefault(); shut(); });   // Esc
    lb.addEventListener('close', () => { if (box.firstChild) shut(); });
    addEventListener('resize', () => { if (lb.open) fill(); });
  }

  /* ---------- scroll-linked: showreel grows to full width, back-to-top appears */
  const top = $('.totop'), reel = $('.reel-frame');
  let ticking = false, lastClip = null, lastTop = null;
  const onScroll = () => {
    if (ticking) return; ticking = true;
    requestAnimationFrame(() => {
      ticking = false;
      if (reel && !RM) {
        // starts narrower (sides cut, full height kept), full width after a short scroll
        const p = Math.min(1, scrollY / (innerHeight * 0.4));
        const clip = p >= 1 ? '' : `inset(0 ${(7 * (1 - p)).toFixed(2)}% round var(--radius))`;
        // only touch the style when it changes: once the reel is full width, scrolling costs nothing
        if (clip !== lastClip) { reel.style.clipPath = clip; lastClip = clip; }
      }
      const on = scrollY > innerHeight * 1.2;
      if (on !== lastTop) { top?.classList.toggle('is-on', on); lastTop = on; }
    });
  };
  lenis ? lenis.on('scroll', onScroll) : addEventListener('scroll', onScroll, { passive: true });
  onScroll();
  // the round button and the "Back to top" link of the footer
  $$('.totop, .ft-top').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    lenis ? lenis.scrollTo(0) : scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' });
    $('.hd-logo')?.focus({ preventScroll: true });
  }));
})();
