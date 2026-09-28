// The on-screen bits drawn with plain HTML: counter, sound button, arrow, messages, start/win cards.
const $ = (id) => document.getElementById(id);

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

let toastTimer = 0;

export const settings = { muted: false };

export const ui = {
  init({ onPlay, onAgain, onSound, onArrow, onSail }) {
    const touch = window.matchMedia('(pointer: coarse)').matches;
    $('how').textContent = touch ? 'Tap or hold where you want to go' : 'Click where you want to go, or use the arrow keys';
    $('play').addEventListener('click', () => {
      $('start').hidden = true;
      $('hud').hidden = false;
      onPlay();
    });
    $('again').addEventListener('click', () => {
      $('win').hidden = true;
      $('hud').hidden = false;
      onAgain();
    });
    settings.muted = store.get('ducks-muted') === '1';
    $('sound').classList.toggle('muted', settings.muted);
    $('sound').addEventListener('click', () => {
      const m = !$('sound').classList.contains('muted');
      $('sound').classList.toggle('muted', m);
      store.set('ducks-muted', m ? '1' : '0');
      settings.muted = m;
      onSound(m);
    });
    $('arrow').addEventListener('click', onArrow);
    $('sail').addEventListener('click', onSail);
    $('winSail').addEventListener('click', () => {
      $('win').hidden = true;
      $('hud').hidden = false;
      onSail();
    });
  },

  // which island is showing: the counter icon and the arrow icon
  setIsland({ icon, arrowIcon, arrowLabel }) {
    document.querySelector('#hud .pill img').src = icon;
    $('arrow').querySelector('img').src = arrowIcon;
    $('arrow').setAttribute('aria-label', arrowLabel);
  },

  // the big "Sail to ..." button at the bottom; null hides it
  sail(label) {
    $('sail').hidden = !label;
    if (label) $('sail').querySelector('span').textContent = label;
  },

  ready() {
    $('play').disabled = false;
    $('play').textContent = 'Play';
  },

  setCount(n, total) {
    $('count').textContent = `${n} / ${total}`;
    const pill = $('count').parentElement;
    pill.classList.remove('bump');
    void pill.offsetWidth;
    pill.classList.add('bump');
  },

  toast(text, ms = 2600) {
    const t = $('toast');
    t.textContent = text;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, ms);
  },

  // x, y: where Mama is on screen (CSS pixels); null hides the arrow
  arrow(pos) {
    const a = $('arrow');
    if (!pos) { a.hidden = true; return; }
    const w = window.innerWidth;
    const h = window.innerHeight;
    const m = 44; // keep clear of the edges
    const top = 76; // and of the top bar
    const cx = w / 2;
    const cy = h / 2;
    const dx = pos.x - cx;
    const dy = pos.y - cy;
    // push the badge out along the line from the centre until it touches the safe box
    const sx = dx > 0 ? (w - m - cx) / dx : dx < 0 ? (m - cx) / dx : Infinity;
    const sy = dy > 0 ? (h - m - cy) / dy : dy < 0 ? (top + m - cy) / dy : Infinity;
    const s = Math.min(sx, sy);
    a.style.transform = `translate(${cx + dx * s}px, ${cy + dy * s}px)`;
    a.style.setProperty('--a', `${(Math.atan2(dy, dx) * 180) / Math.PI + 90}deg`);
    a.hidden = false;
  },

  win({ title, text, icon, sailLabel }) {
    $('win').querySelector('h1').textContent = title;
    $('win').querySelector('p').textContent = text;
    $('win').querySelector('.hero').src = icon;
    $('winSail').querySelector('span').textContent = sailLabel;
    $('hud').hidden = true;
    $('arrow').hidden = true;
    $('sail').hidden = true;
    $('win').hidden = false;
  },
};
