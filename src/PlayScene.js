import Phaser from 'phaser';
import level from './level.json';
import info from './assetInfo.json';
import { Nav, inPoly } from './nav.js';
import { ui, settings } from './ui.js';
import { preloadBoat, setupBoat, boatTick, ISLANDS } from './boat.js';

const SPEED = 165;        // capybara walking speed, island pixels per second
// characters and hiding spots are stored at 2x with the island's chunky pixels (see tools/prep_assets.py)
const CAPY_SCALE = 0.5;
const DUCK_SCALE = 0.5;
const CHICK_SCALE = 0.5;
const SPOT_SCALE = 0.5;
const FIND_RANGE = 62;    // how close you must get to a hiding duckling
const HINT_RANGE = 420;   // hiding ducklings quack when you are this close
const FIRST_GAP = 36;     // space between the capybara and the first duckling
const GAP = 28;           // space between ducklings in the line
const HOME = level.homeZone;
const PEN = { x0: 286, y0: 188, x1: 662, y1: 444 }; // Mama's pen: tapping inside it means "go to the gate"
const PLAY_VIEW = 440;    // how many island pixels fit across the short side of the screen

const IDLE = { down: 0, left: 4, right: 8, up: 12 };
const CHICK = { down: 0, left: 4, right: 7, up: 2 };
const QUACKS = ['quack_01', 'quack_02', 'quack_03'];

let navCache = null; // the walk map never changes, so build it once

export class PlayScene extends Phaser.Scene {
  constructor() {
    super('play');
  }

  init(data) {
    this.playing = !!data.autoStart;
    this.initData = data;
  }

  preload() {
    this.load.image('island', 'assets/island.webp');
    for (const k of ['capy', 'duck', 'duckling']) {
      this.load.spritesheet(k, `assets/${k}.png`, { frameWidth: info[k].frameWidth, frameHeight: info[k].frameHeight });
    }
    for (const k of info.spots) this.load.image(k, `assets/${k}.png`);
    for (const k of Object.keys(info.trees)) this.load.image(k, `assets/${k}.png`);
    this.load.atlas('props', 'assets/props.png', 'assets/props.json');
    this.load.image('heart', 'assets/heart_px.png');
    for (const k of [...QUACKS, 'pickup_blip', 'yay_chime']) this.load.audio(k, `assets/audio/${k}.wav`);
    preloadBoat(this);
  }

  create() {
    this.sound.mute = settings.muted;
    this.add.image(0, 0, 'island').setOrigin(0).setScale(1 / info.map.textureScale).setDepth(-1e5);

    // hiding spots (bushes, logs, rocks, stumps); you can't walk through them
    const coverWalls = [];
    this.occluders = []; // things drawn over the capybara when it walks behind them
    this.spots = level.spots.map((s, i) => {
      const img = this.add.image(s.x, s.y, info.spots[i]).setOrigin(0.5, 1).setScale(SPOT_SCALE).setDepth(s.y);
      const w = img.displayWidth;
      const h = img.displayHeight;
      this.occluders.push({ img, base: s.y, box: img.getBounds() });
      coverWalls.push({ type: 'ellipse', x: s.x, y: s.y - h * 0.28, rx: w * 0.4, ry: h * 0.24 });
      return { ...s, img, w, h };
    });
    // treetops are drawn over the capybara when it walks behind them; only the trunks are solid
    for (const [key, t] of Object.entries(info.trees)) {
      const img = this.add.image(t.x, t.y, key).setOrigin(0).setScale(1 / info.map.textureScale).setDepth(t.base);
      this.occluders.push({ img, base: t.base, box: img.getBounds() });
      // the strip between the bottom of the leaves and the roots is solid, so the capybara is either
      // fully under the leaves or out in front, never half-hidden with its legs poking out
      coverWalls.push({ type: 'ellipse', x: t.trunkX, y: t.base - 24, rx: img.displayWidth * 0.42, ry: 22 });
    }
    // same for the painted bushes, rocks, stumps, logs and lamps: only their bottom edge is solid
    for (const [key, pr] of Object.entries(info.props)) {
      const img = this.add.image(pr.x, pr.y, 'props', key).setOrigin(0).setScale(1 / info.map.textureScale).setDepth(pr.base);
      this.occluders.push({ img, base: pr.base, box: img.getBounds() });
      coverWalls.push({ type: 'ellipse', ...pr.foot });
    }
    navCache ??= new Nav({
      width: info.map.width,
      height: info.map.height,
      start: level.start,
      ground: (x, y) => inPoly(level.walkable, x, y),
      blockers: [...level.blockers, ...coverWalls],
    });
    this.nav = navCache;

    if (!this.anims.exists('walk-down')) {
      for (const [dir, f] of Object.entries(IDLE)) {
        this.anims.create({ key: `walk-${dir}`, frames: this.anims.generateFrameNumbers('capy', { start: f, end: f + 3 }), frameRate: 9, repeat: -1 });
      }
    }

    // the player
    const [sx, sy] = level.start;
    this.player = this.add.sprite(sx, sy, 'capy', IDLE.down).setOrigin(0.5, 0.97).setScale(CAPY_SCALE);
    this.player.shadow = this.makeShadow(44, 13);
    this.facing = 'down';
    this.path = null;
    this.trail = [];

    // Mama Duck in her pen
    const [mx, my] = level.mommy;
    this.mama = this.add.sprite(mx, my, 'duck', 0).setOrigin(0.5, 0.95).setScale(DUCK_SCALE);
    Object.assign(this.mama, { gx: mx, gy: my, hop: 0 });
    this.mama.shadow = this.makeShadow(40, 12);

    // lost ducklings, each peeking out from the side of a random spot you can walk up to
    this.chicks = [];
    for (const s of Phaser.Utils.Array.Shuffle(this.spots.slice())) {
      if (this.chicks.length === level.ducklings) break;
      const gy = s.y - s.h * 0.18;
      const sides = [-1, 1].filter((side) => this.nav.canReach(s.x + side * s.w * 0.45, gy, 50));
      if (!sides.length) continue;
      const side = Phaser.Utils.Array.GetRandom(sides);
      const c = this.add.sprite(0, 0, 'duckling', side < 0 ? CHICK.left : CHICK.right).setOrigin(0.5, 0.95).setScale(CHICK_SCALE);
      Object.assign(c, { gx: s.x + side * s.w * 0.45, gy, hop: 0, state: 'hidden', spot: s, nextHint: 0 });
      c.shadow = this.makeShadow(22, 7);
      this.chicks.push(c);
    }
    this.total = this.chicks.length;
    this.followers = [];
    this.homeCount = 0;
    this.slotsUsed = 0;
    this.foundAny = false;

    // controls
    this.keys = this.input.keyboard.addKeys('UP,DOWN,LEFT,RIGHT,W,A,S,D');
    this.holding = false;
    this.nextRepath = 0;
    this.input.on('pointerdown', (p) => {
      if (!this.playing) return;
      this.holding = true;
      const w = this.cameras.main.getWorldPoint(p.x, p.y);
      if (this.boat.contains(w.x, w.y)) { this.holding = false; this.walkTo(...this.boat.board, true); return; }
      this.walkTo(w.x, w.y, true);
    });
    this.input.on('pointerup', () => { this.holding = false; });
    this.input.on('gameout', () => { this.holding = false; });

    // camera
    const cam = this.cameras.main;
    cam.setBackgroundColor('#4cc1e6');
    this.fitCamera();
    this.scale.on('resize', this.fitCamera, this);
    this.events.once('shutdown', () => this.scale.off('resize', this.fitCamera, this));

    this.arrowShown = false;
    setupBoat(this, level.boat, this.initData);
    this.showHud();
    ui.ready();
  }

  // ---------- camera

  playZoom() {
    const w = this.scale.width;
    const h = this.scale.height;
    return Math.max(Math.min(w, h) / PLAY_VIEW, w / info.map.width, h / info.map.height);
  }

  fitCamera() {
    const cam = this.cameras.main;
    cam.setSize(this.scale.width, this.scale.height);
    if (this.playing || this.sailing) {
      cam.setZoom(this.playZoom());
      cam.setBounds(0, 0, info.map.width, info.map.height);
      cam.startFollow(this.camTarget || this.player, false, 0.15, 0.15);
    } else {
      // title screen: show the whole island
      cam.stopFollow();
      cam.removeBounds();
      cam.setZoom(Math.min(this.scale.width / info.map.width, this.scale.height / info.map.height) * 1.02);
      cam.centerOn(info.map.width / 2, info.map.height / 2);
    }
  }

  begin() {
    if (this.playing) return;
    const cam = this.cameras.main;
    cam.pan(this.player.x, this.player.y, 900, 'Sine.easeInOut');
    cam.zoomTo(this.playZoom(), 900, 'Sine.easeInOut', false, (c, t) => {
      if (t < 1) return;
      this.playing = true;
      this.fitCamera();
      ui.toast('Listen for quacks!');
    });
  }

  // ---------- helpers

  makeShadow(w, h) {
    return this.add.ellipse(0, 0, w, h, 0x2b4a1a, 0.22);
  }

  quack(volume, small) {
    this.sound.play(Phaser.Utils.Array.GetRandom(QUACKS), {
      volume,
      detune: small ? Phaser.Math.Between(350, 650) : Phaser.Math.Between(-150, 100),
    });
  }

  hearts(x, y, n = 1) {
    for (let i = 0; i < n; i++) {
      const h = this.add.image(x + (n > 1 ? Phaser.Math.Between(-26, 26) : 0), y, 'heart').setScale(0.5).setDepth(1e6);
      this.tweens.add({
        targets: h,
        y: y - 42 - Math.random() * 18,
        alpha: 0,
        duration: 900,
        delay: i * 90,
        ease: 'Quad.easeOut',
        onComplete: () => h.destroy(),
      });
    }
  }

  hopOnce(target, height, times = 1) {
    this.tweens.add({ targets: target, hop: height, duration: 150, yoyo: true, repeat: times - 1, ease: 'Quad.easeOut' });
  }

  walkTo(x, y, showMarker) {
    // tapping the pen means "go to the gate"
    if (x > PEN.x0 && x < PEN.x1 && y > PEN.y0 && y < PEN.y1) {
      x = HOME.x;
      y = HOME.y;
    }
    this.path = this.nav.findPath(this.player.x, this.player.y, x, y);
    this.lastTarget = { x, y };
    if (showMarker && this.path) {
      const end = this.path[this.path.length - 1];
      const ring = this.add.ellipse(end.x, end.y, 26, 14).setStrokeStyle(3, 0xffffff, 0.95).setDepth(end.y - 2);
      this.tweens.add({ targets: ring, scale: 1.8, alpha: 0, duration: 500, onComplete: () => ring.destroy() });
    }
  }

  goToGoal() {
    this.goHome();
  }

  // ---------- the boat (see boat.js)

  showHud() {
    ui.setIsland({ icon: 'assets/ui_duckling.png', arrowIcon: 'assets/ui_duck.png', arrowLabel: 'Go to Mama Duck' });
    ui.setCount(this.homeCount, this.total);
  }

  landed() {
    this.facing = 'up';
    this.player.anims.stop();
    this.player.setFrame(IDLE.up);
    this.trail = [];
  }

  onArrive() {
    const left = this.total - this.homeCount;
    ui.toast(left ? `Sunny Meadow! ${left} ducklings are lost. Listen for quacks!` : 'Back on Sunny Meadow. All the ducklings are home.');
  }

  cantSail() {
    return this.followers.length ? 'Take the ducklings home to Mama first!' : null;
  }

  goHome() {
    if (this.playing) this.walkTo(HOME.x, HOME.y, true);
  }

  tryMove(dx, dy) {
    const p = this.player;
    const nav = this.nav;
    if (nav.canStand(p.x + dx, p.y + dy)) { p.x += dx; p.y += dy; return true; }
    if (dx && nav.canStand(p.x + dx, p.y)) { p.x += dx; return true; }
    if (dy && nav.canStand(p.x, p.y + dy)) { p.y += dy; return true; }
    return false;
  }

  // a point on the capybara's recent footsteps, `dist` pixels behind it
  trailPoint(dist) {
    let acc = 0;
    let prev = { x: this.player.x, y: this.player.y };
    for (const q of this.trail) {
      const seg = Math.hypot(q.x - prev.x, q.y - prev.y);
      if (acc + seg >= dist) {
        const t = seg ? (dist - acc) / seg : 0;
        return { x: prev.x + (q.x - prev.x) * t, y: prev.y + (q.y - prev.y) * t };
      }
      acc += seg;
      prev = q;
    }
    return prev;
  }

  // ---------- game events

  pickUp(c) {
    this.tweens.killTweensOf(c);
    c.hop = 0;
    c.state = 'following';
    this.followers.push(c);
    this.hearts(c.gx, c.gy - 34);
    this.sound.play('pickup_blip', { volume: 0.6 });
    this.quack(0.7, true);
    c.setScale(CHICK_SCALE * 1.3);
    this.tweens.add({ targets: c, scale: CHICK_SCALE, duration: 300, ease: 'Back.easeOut' });
    if (!this.foundAny) {
      this.foundAny = true;
      ui.toast('You found one! Take it home to Mama Duck.');
    }
  }

  deliver() {
    const group = this.followers.splice(0);
    this.quack(0.8);
    this.hopOnce(this.mama, 14, 2);
    group.forEach((c, i) => {
      c.state = 'flying';
      const [tx, ty] = level.homeSlots[this.slotsUsed++ % level.homeSlots.length];
      this.time.delayedCall(i * 280, () => {
        const fx = c.gx;
        const fy = c.gy;
        this.tweens.addCounter({
          from: 0,
          to: 1,
          duration: 750,
          ease: 'Sine.easeInOut',
          onUpdate: (tw) => {
            const t = tw.getValue();
            c.gx = fx + (tx - fx) * t;
            c.gy = fy + (ty - fy) * t;
            c.hop = 70 * 4 * t * (1 - t); // jump over the fence
            c.setFlipX(false).setFrame(ty < fy ? CHICK.up : CHICK.down);
          },
          onComplete: () => this.arrive(c),
        });
      });
    });
  }

  arrive(c) {
    c.state = 'home';
    c.hop = 0;
    c.setFrame(CHICK.down).setFlipX(c.gx > this.mama.gx);
    this.homeCount++;
    ui.setCount(this.homeCount, this.total);
    this.hearts(c.gx, c.gy - 34, 2);
    this.sound.play('pickup_blip', { volume: 0.5 });
    this.quack(0.6, true);
    if (this.homeCount === this.total) this.win();
    else if (this.homeCount === 1) this.time.delayedCall(700, () => ui.toast(`Yay! ${this.total - 1} more to find.`));
  }

  win() {
    this.playing = false;
    this.path = null;
    this.player.anims.stop();
    this.player.setFrame(IDLE.down);
    this.sound.play('yay_chime', { volume: 0.8 });
    this.hopOnce(this.mama, 18, 3);
    this.hearts(this.mama.gx, this.mama.gy - 50, 6);
    for (const c of this.chicks) this.hopOnce(c, 12, 3);
    this.time.delayedCall(1600, () => ui.win({
      title: 'All home!',
      text: 'Mama Duck is so happy. Thank you!',
      icon: 'assets/ui_duck.png',
      sailLabel: ISLANDS.school.sailLabel,
    }));
  }

  // ---------- every frame

  update(time, delta) {
    const dt = Math.min(delta, 50) / 1000;
    const p = this.player;
    const ox = p.x;
    const oy = p.y;

    if (this.playing) {
      const k = this.keys;
      const kx = (k.RIGHT.isDown || k.D.isDown ? 1 : 0) - (k.LEFT.isDown || k.A.isDown ? 1 : 0);
      const ky = (k.DOWN.isDown || k.S.isDown ? 1 : 0) - (k.UP.isDown || k.W.isDown ? 1 : 0);
      if (kx || ky) {
        this.path = null;
        const len = Math.hypot(kx, ky);
        this.tryMove((kx / len) * SPEED * dt, (ky / len) * SPEED * dt);
      } else {
        // holding a finger down: keep heading for it, even as the view scrolls
        if (this.holding && time > this.nextRepath) {
          this.nextRepath = time + 150;
          const ptr = this.input.activePointer;
          if (ptr.isDown) {
            const w = this.cameras.main.getWorldPoint(ptr.x, ptr.y);
            const lt = this.lastTarget;
            if (!lt || Math.hypot(w.x - lt.x, w.y - lt.y) > 12) this.walkTo(w.x, w.y, false);
          } else {
            this.holding = false;
          }
        }
        if (this.path && this.path.length) {
          let step = SPEED * dt;
          while (step > 0 && this.path.length) {
            const t = this.path[0];
            const d = Math.hypot(t.x - p.x, t.y - p.y);
            if (d <= step) {
              if (!this.tryMove(t.x - p.x, t.y - p.y)) { this.path = null; break; }
              this.path.shift();
              step -= d;
            } else {
              if (!this.tryMove(((t.x - p.x) / d) * step, ((t.y - p.y) / d) * step)) this.path = null;
              break;
            }
          }
        }
      }
    }

    // walking animation
    const mx = p.x - ox;
    const my = p.y - oy;
    if (Math.abs(mx) + Math.abs(my) > 0.01) {
      let dir = this.facing;
      const horiz = dir === 'left' || dir === 'right';
      // small bias toward the current direction stops flicker on diagonals
      if (Math.abs(mx) > Math.abs(my) * (horiz ? 0.8 : 1.25)) dir = mx < 0 ? 'left' : 'right';
      else dir = my < 0 ? 'up' : 'down';
      if (dir !== this.facing || !p.anims.isPlaying) p.play(`walk-${dir}`, true);
      this.facing = dir;
      const last = this.trail[0];
      if (!last || Math.hypot(p.x - last.x, p.y - last.y) >= 3) {
        this.trail.unshift({ x: p.x, y: p.y });
        if (this.trail.length > 500) this.trail.length = 500;
      }
    } else if (p.anims.isPlaying) {
      p.anims.stop();
      p.setFrame(IDLE[this.facing]);
    }
    p.setDepth(p.y);
    p.shadow.setPosition(p.x, p.y - 2).setDepth(p.y - 0.5);

    // ducklings following in a line
    this.followers.forEach((c, i) => {
      const t = this.trailPoint(FIRST_GAP + i * GAP);
      const k = Math.min(1, dt * 9);
      const vx = (t.x - c.gx) * k;
      const vy = (t.y - c.gy) * k;
      c.gx += vx;
      c.gy += vy;
      const moving = Math.abs(vx) + Math.abs(vy) > 0.15;
      if (moving) {
        if (Math.abs(vx) > Math.abs(vy)) c.setFrame(vx < 0 ? CHICK.left : CHICK.right);
        else c.setFrame(vy < 0 ? CHICK.up : CHICK.down);
      }
      c.rotation = moving ? Math.sin(time / 70 + i) * 0.14 : 0;
    });

    // hiding ducklings: found when close, quack as a hint when nearby
    if (this.playing) {
      for (const c of this.chicks) {
        if (c.state !== 'hidden') continue;
        const d = Math.hypot(p.x - c.gx, p.y - c.gy);
        if (d < FIND_RANGE) {
          this.pickUp(c);
        } else if (d < HINT_RANGE && time > c.nextHint) {
          c.nextHint = time + 2600 + Math.random() * 2600;
          this.hopOnce(c, 10);
          // a little wiggle around the size the spot is drawn at (level.json's scale is already in the picture);
          // start from rest so two wiggles can never stack up and leave it the wrong size
          const img = c.spot.img;
          this.tweens.killTweensOf(img);
          img.setScale(SPOT_SCALE);
          this.tweens.add({ targets: img, scaleX: SPOT_SCALE * 1.06, scaleY: SPOT_SCALE * 0.95, duration: 110, yoyo: true, repeat: 1 });
          this.quack(Phaser.Math.Clamp(1 - d / HINT_RANGE, 0.15, 0.7), true);
        }
      }
      if (this.followers.length && Math.hypot(p.x - HOME.x, p.y - HOME.y) < HOME.r) this.deliver();
    }

    // Mama looks at you
    this.mama.setFlipX(p.x > this.mama.gx);

    // place every duck (feet on the ground, hop lifts the picture)
    for (const d of [this.mama, ...this.chicks]) {
      const bob = d === this.mama ? (Math.floor(time / 450) % 2) * 2 : 0; // Mama bobs one pixel-step
      d.setPosition(d.gx, d.gy - d.hop - bob);
      d.setDepth(d.state === 'hidden' ? d.spot.y - 1 : d.gy);
      d.shadow.setPosition(d.gx, d.gy - 1).setDepth(d.depth - 0.5);
      d.shadow.setScale(1 - Math.min(d.hop, 60) / 120);
    }

    this.fadeOccluders(dt);
    boatTick(this, time);
    this.updateArrow();
  }

  // whatever the capybara is standing behind turns see-through, so it never gets lost
  fadeOccluders(dt) {
    const p = this.player;
    const cx = p.x;
    const cy = p.y - 24; // middle of the capybara
    const k = Math.min(1, dt * 10);
    for (const o of this.occluders) {
      const b = o.box;
      const behind = p.y < o.base && cx > b.x && cx < b.right && cy > b.y && cy < b.bottom;
      const target = behind ? 0.45 : 1;
      if (o.img.alpha !== target) o.img.alpha += (target - o.img.alpha) * k;
      if (Math.abs(o.img.alpha - target) < 0.01) o.img.alpha = target;
    }
  }

  // arrow at the screen edge pointing to Mama while ducklings are following you
  updateArrow() {
    let pos = null;
    if (this.playing && this.followers.length) {
      const cam = this.cameras.main;
      const v = cam.worldView;
      const m = this.mama;
      const onScreen = m.gx > v.x + 16 && m.gx < v.right - 16 && m.gy - 40 > v.y && m.gy < v.bottom - 8;
      if (!onScreen) {
        const css = cam.zoom * this.scale.zoom;
        pos = { x: (m.gx - v.x) * css, y: (m.gy - 25 - v.y) * css };
      }
    }
    if (pos || this.arrowShown) ui.arrow(pos);
    this.arrowShown = !!pos;
  }
}
