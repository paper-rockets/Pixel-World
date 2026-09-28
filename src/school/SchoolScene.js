import Phaser from 'phaser';
import info from './assets.json';
import { Nav } from '../nav.js';
import { ui, settings } from '../ui.js';
import { preloadBoat, setupBoat, boatTick, ISLANDS } from '../boat.js';

const SPEED = 165;        // walking speed, island pixels per second
const PICK_RANGE = 40;    // how close you must get to a flower
const GARDEN_RANGE = 28;  // how close to the garden's stone ring to plant flowers
const PLAY_VIEW = 440;    // how many island pixels fit across the short side of the screen
const IDLE = { down: 0, left: 4, right: 8, up: 12 };
const TEX = 0.5;          // every picture is stored at 2x

let navCache = null;

export class SchoolScene extends Phaser.Scene {
  constructor() {
    super('school');
  }

  init(data) {
    this.playing = !!data.autoStart;
    this.initData = data;
  }

  preload() {
    this.load.image('ground', 'school/ground.webp');
    this.load.image('walk', 'school/walk.png');
    this.load.image('schoolhouse', 'school/school.png');
    this.load.atlas('things', 'school/objects.png', 'school/objects.json');
    this.load.spritesheet('capy', 'school/capy.png', { frameWidth: info.capy.frameWidth, frameHeight: info.capy.frameHeight });
    this.load.audio('pickup', 'assets/audio/pickup_blip.wav');
    this.load.audio('chime', 'assets/audio/yay_chime.wav');
    preloadBoat(this);
  }

  create() {
    this.sound.mute = settings.muted;
    const [W, H] = info.size;
    this.add.image(0, 0, 'ground').setOrigin(0).setScale(TEX).setDepth(-1e5);

    // everything standing on the island; drawn in order of where it touches the ground
    const walls = info.blockRects.map(([x0, y0, x1, y1]) => ({ type: 'rect', x: x0, y: y0, w: x1 - x0, h: y1 - y0 }));
    this.flowers = [];
    this.occluders = [];
    for (const o of info.objects) {
      const img = o.id === 'school'
        ? this.add.image(o.x, o.y, 'schoolhouse')
        : this.add.image(o.x, o.y, 'things', o.id);
      img.setOrigin(0).setScale(TEX).setDepth(o.ground ? -1e4 + o.base : o.base);
      if (o.foot) walls.push(o.foot);
      if (o.role === 'flower') {
        this.flowers.push({ img, x: o.x + o.w / 2, y: o.base, top: o.y, state: 'waiting', nextSparkle: 0 });
      } else if (o.role === 'garden') {
        this.garden = { img, x: o.x + o.w / 2, y: o.base - o.h * 0.42, rx: o.w * 0.46, ry: o.h * 0.4, box: o };
      } else if (!o.ground && o.id !== 'school') {
        this.occluders.push({ img, base: o.base, box: img.getBounds() });
      }
    }
    this.total = this.flowers.length;

    // where you can walk comes from the ground picture itself (walk.png: white = walkable)
    if (!navCache) {
      const src = this.textures.get('walk').getSourceImage();
      const cv = document.createElement('canvas');
      cv.width = src.width;
      cv.height = src.height;
      const ctx = cv.getContext('2d');
      ctx.drawImage(src, 0, 0);
      const px = ctx.getImageData(0, 0, src.width, src.height).data;
      const cell = info.walk.cell;
      const ground = (x, y) => {
        const c = Math.floor(x / cell);
        const r = Math.floor(y / cell);
        if (c < 0 || r < 0 || c >= src.width || r >= src.height) return false;
        return px[(r * src.width + c) * 4] > 127;
      };
      navCache = new Nav({ width: W, height: H, start: info.start, ground, blockers: walls });
    }
    this.nav = navCache;

    if (!this.anims.exists('walk-down')) {
      for (const [dir, f] of Object.entries(IDLE)) {
        this.anims.create({ key: `walk-${dir}`, frames: this.anims.generateFrameNumbers('capy', { start: f, end: f + 3 }), frameRate: 9, repeat: -1 });
      }
    }

    const [sx, sy] = info.start;
    this.player = this.add.sprite(sx, sy, 'capy', IDLE.up).setOrigin(0.5, 1).setScale(TEX);
    this.player.shadow = this.add.ellipse(sx, sy, 34, 10, 0x2b4a1a, 0.22);
    this.facing = 'up';
    this.path = null;
    this.carried = 0;
    this.planted = 0;
    this.toldGarden = false;

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

    this.cameras.main.setBackgroundColor('#3fc3ea');
    this.fitCamera();
    this.scale.on('resize', this.fitCamera, this);
    this.events.once('shutdown', () => this.scale.off('resize', this.fitCamera, this));

    this.arrowShown = false;
    setupBoat(this, info.boat, this.initData);
    this.showHud();
    ui.ready();
  }

  // ---------- camera

  playZoom() {
    const [W, H] = info.size;
    const w = this.scale.width;
    const h = this.scale.height;
    return Math.max(Math.min(w, h) / PLAY_VIEW, w / W, h / H);
  }

  fitCamera() {
    const [W, H] = info.size;
    const cam = this.cameras.main;
    cam.setSize(this.scale.width, this.scale.height);
    if (this.playing || this.sailing) {
      cam.setZoom(this.playZoom());
      cam.setBounds(0, 0, W, H);
      cam.startFollow(this.camTarget || this.player, false, 0.15, 0.15);
    } else {
      cam.stopFollow();
      cam.removeBounds();
      cam.setZoom(Math.min(this.scale.width / W, this.scale.height / H) * 1.02);
      cam.centerOn(W / 2, H / 2);
    }
  }

  begin() {
    if (this.playing) return;
    const cam = this.cameras.main;
    cam.pan(this.player.x, this.player.y - 40, 900, 'Sine.easeInOut');
    cam.zoomTo(this.playZoom(), 900, 'Sine.easeInOut', false, (c, t) => {
      if (t < 1) return;
      this.playing = true;
      this.fitCamera();
      ui.toast('Look for orange flowers!');
    });
  }

  // ---------- walking

  walkTo(x, y, showMarker) {
    this.path = this.nav.findPath(this.player.x, this.player.y, x, y);
    this.lastTarget = { x, y };
    if (showMarker && this.path) {
      const end = this.path[this.path.length - 1];
      const ring = this.add.ellipse(end.x, end.y, 26, 14).setStrokeStyle(3, 0xffffff, 0.95).setDepth(end.y - 2);
      this.tweens.add({ targets: ring, scale: 1.8, alpha: 0, duration: 500, onComplete: () => ring.destroy() });
    }
  }

  goToGoal() {
    this.goToGarden();
  }

  // ---------- the boat (see boat.js)

  showHud() {
    ui.setIsland({ icon: 'school/ui_flower.png', arrowIcon: 'school/ui_garden.png', arrowLabel: 'Go to the garden' });
    ui.setCount(this.planted + this.carried, this.total);
  }

  landed() {
    this.facing = 'up';
    this.player.anims.stop();
    this.player.setFrame(IDLE.up);
  }

  onArrive() {
    if (this.planted === this.total) ui.toast('Back at the school. The garden is still blooming.');
    else if (this.planted + this.carried === 0) ui.toast('The school! Find 5 orange flowers for the garden.');
    else ui.toast('Back at the school. Keep looking for orange flowers!');
  }

  goToGarden() {
    if (!this.playing) return;
    const g = this.garden;
    this.walkTo(g.x, g.y + g.ry + 14, true);
  }

  tryMove(dx, dy) {
    const p = this.player;
    const nav = this.nav;
    if (nav.canStand(p.x + dx, p.y + dy)) { p.x += dx; p.y += dy; return true; }
    if (dx && nav.canStand(p.x + dx, p.y)) { p.x += dx; return true; }
    if (dy && nav.canStand(p.x, p.y + dy)) { p.y += dy; return true; }
    return false;
  }

  // ---------- flowers and the garden

  sparkle(x, y, color = 0xffffff) {
    const s = this.add.rectangle(x, y, 3, 3, color).setDepth(1e6);
    this.tweens.add({ targets: s, y: y - 10, alpha: 0, duration: 700, ease: 'Quad.easeOut', onComplete: () => s.destroy() });
  }

  pickUp(f) {
    f.state = 'carried';
    this.carried++;
    this.sound.play('pickup', { volume: 0.6 });
    // the flower floats up to the capybara and tucks away
    this.tweens.add({
      targets: f.img,
      x: this.player.x - f.img.displayWidth / 2,
      y: this.player.y - 70,
      alpha: 0,
      duration: 500,
      ease: 'Quad.easeIn',
      onComplete: () => f.img.setVisible(false),
    });
    for (let i = 0; i < 5; i++) this.time.delayedCall(i * 60, () => this.sparkle(f.x + Phaser.Math.Between(-10, 10), f.top + 12, 0xffd08a));
    const found = this.planted + this.carried;
    ui.setCount(found, this.total);
    if (!this.toldGarden) {
      this.toldGarden = true;
      ui.toast('Take the flowers to the garden by the school.');
    } else if (found === this.total && this.carried) {
      ui.toast('All found! Take them to the garden.');
    }
  }

  plant() {
    const n = this.carried;
    this.carried = 0;
    const g = this.garden;
    for (let i = 0; i < n; i++) {
      const slot = this.planted + i;
      const a = (slot / this.total) * Math.PI * 2 + 0.4;
      const fx = g.x + Math.cos(a) * g.rx * 0.45;
      const fy = g.y + Math.sin(a) * g.ry * 0.35 + 4;
      this.time.delayedCall(i * 350, () => {
        const f = this.add.image(fx, fy, 'things', `flower-${(slot % 5) + 1}`).setOrigin(0.5, 1).setScale(TEX * 0.7).setDepth(g.box.base + 1).setAlpha(0);
        this.tweens.add({ targets: f, alpha: 1, y: fy, duration: 400 });
        for (let k = 0; k < 4; k++) this.sparkle(fx + Phaser.Math.Between(-8, 8), fy - 10, 0xffd08a);
        this.sound.play('pickup', { volume: 0.4, detune: 300 + slot * 100 });
      });
    }
    this.planted += n;
    if (this.planted === this.total) this.time.delayedCall(n * 350 + 300, () => this.bloom());
    else this.time.delayedCall(n * 350, () => ui.toast(`${this.total - this.planted} more to find.`));
  }

  bloom() {
    this.playing = false;
    this.path = null;
    this.player.anims.stop();
    this.player.setFrame(IDLE[this.facing]);
    this.sound.play('chime', { volume: 0.7 });
    // the garden gently glows
    const g = this.garden;
    const glow = this.add.ellipse(g.x, g.y, g.rx * 2.4, g.ry * 2.6, 0xffe2a8, 0).setDepth(g.box.base + 2).setBlendMode(Phaser.BlendModes.ADD);
    this.tweens.add({ targets: glow, fillAlpha: 0.35, duration: 900, yoyo: true, repeat: 1, ease: 'Sine.easeInOut' });
    for (let i = 0; i < 16; i++) this.time.delayedCall(i * 90, () => this.sparkle(g.x + Phaser.Math.Between(-g.rx, g.rx), g.y + Phaser.Math.Between(-g.ry, g.ry / 2), 0xfff3c4));
    this.time.delayedCall(2200, () => ui.win({
      title: 'The garden is blooming',
      text: 'Thank you for helping it grow.',
      icon: 'school/ui_garden.png',
      sailLabel: ISLANDS.play.sailLabel,
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
      if (Math.abs(mx) > Math.abs(my) * (horiz ? 0.8 : 1.25)) dir = mx < 0 ? 'left' : 'right';
      else dir = my < 0 ? 'up' : 'down';
      if (dir !== this.facing || !p.anims.isPlaying) p.play(`walk-${dir}`, true);
      this.facing = dir;
    } else if (p.anims.isPlaying) {
      p.anims.stop();
      p.setFrame(IDLE[this.facing]);
    }
    p.setDepth(p.y);
    p.shadow.setPosition(p.x, p.y - 2).setDepth(p.y - 0.5);

    if (this.playing) {
      // flowers: gentle one-pixel bob and a sparkle now and then; picked up when you are close
      for (const f of this.flowers) {
        if (f.state !== 'waiting') continue;
        f.img.y = f.top - (Math.floor((time + f.x * 7) / 600) % 2) * 1;
        if (time > f.nextSparkle) {
          f.nextSparkle = time + 1200 + Math.random() * 1500;
          this.sparkle(f.x + Phaser.Math.Between(-8, 8), f.top + Phaser.Math.Between(4, 14));
        }
        if (Math.hypot(p.x - f.x, p.y - f.y) < PICK_RANGE) this.pickUp(f);
      }
      // plant whatever you carry when you reach the garden's stone ring
      const g = this.garden;
      if (this.carried) {
        const dx = (p.x - g.x) / (g.rx + GARDEN_RANGE);
        const dy = (p.y - g.y) / (g.ry + GARDEN_RANGE);
        if (dx * dx + dy * dy < 1) this.plant();
      }
    }

    this.fadeOccluders(dt);
    boatTick(this, time);
    this.updateArrow();
  }

  // whatever the capybara is standing behind turns see-through, so it never gets lost
  fadeOccluders(dt) {
    const p = this.player;
    const cx = p.x;
    const cy = p.y - 24;
    const k = Math.min(1, dt * 10);
    for (const o of this.occluders) {
      const b = o.box;
      const behind = p.y < o.base && cx > b.x && cx < b.right && cy > b.y && cy < b.bottom;
      const target = behind ? 0.45 : 1;
      if (o.img.alpha !== target) o.img.alpha += (target - o.img.alpha) * k;
      if (Math.abs(o.img.alpha - target) < 0.01) o.img.alpha = target;
    }
  }

  // arrow at the screen edge pointing to the garden while you carry flowers
  updateArrow() {
    let pos = null;
    if (this.playing && this.carried) {
      const cam = this.cameras.main;
      const v = cam.worldView;
      const g = this.garden;
      const onScreen = g.x > v.x + 16 && g.x < v.right - 16 && g.y - 20 > v.y && g.y < v.bottom - 8;
      if (!onScreen) {
        const css = cam.zoom * this.scale.zoom;
        pos = { x: (g.x - v.x) * css, y: (g.y - v.y) * css };
      }
    }
    if (pos || this.arrowShown) ui.arrow(pos);
    this.arrowShown = !!pos;
  }
}
