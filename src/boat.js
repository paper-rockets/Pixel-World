// The rowing boat that carries the capybara between the islands.
// Each island scene has: this.boat (a Boat), this.player, this.playing, this.path, fitCamera(),
// landed() (put the capybara on the dock) and onArrive() (the welcome message).
import boatInfo from './boatInfo.json';
import { ui } from './ui.js';

const TEX = 0.5;                // boat pictures are stored at 2x
const WATER = [76, 193, 230];   // fade through the colour of the sea
const TRIP = 330;               // how far the boat rows on and off screen, island pixels
const BOARD_RANGE = 44;         // how close to the dock end the sail button appears

export const ISLANDS = {
  play: { sailLabel: 'Sail to Sunny Meadow' },
  school: { sailLabel: 'Sail to the school' },
};
export const otherIsland = (key) => (key === 'play' ? 'school' : 'play');

export function preloadBoat(scene) {
  for (const kind of ['empty', 'capy']) {
    for (const d of ['up', 'down', 'left', 'right']) scene.load.image(`boat_${kind}_${d}`, `boat/boat_${kind}_${d}.png`);
  }
  for (const d of ['up', 'down']) {
    for (let f = 1; f <= 4; f++) scene.load.image(`wake_${d}_${f}`, `boat/wake_${d}_${f}.png`);
  }
}

export class Boat {
  // x, y: middle of the moored boat; dir: which way it points while moored; board: dock spot next to it
  constructor(scene, { x, y, dir, board }) {
    this.scene = scene;
    this.home = { x, y };
    this.dir = dir;
    this.board = board;
    this.x = x;
    this.y = y;
    this.moving = null; // 'up' or 'down' while rowing
    this.wake = scene.add.image(x, y, 'wake_down_1').setScale(TEX).setVisible(false);
    this.sprite = scene.add.image(x, y, `boat_empty_${dir}`).setScale(TEX);
  }

  show(kind, dir) {
    this.sprite.setTexture(`boat_${kind}_${dir}`);
  }

  contains(x, y) {
    return this.sprite.getBounds().contains(x, y);
  }

  // row straight up or down by dy; resolves when the boat stops
  row(dy, duration, ease) {
    this.moving = dy > 0 ? 'down' : 'up';
    return new Promise((done) => {
      this.scene.tweens.add({
        targets: this,
        y: this.y + dy,
        duration,
        ease,
        onComplete: () => { this.moving = null; done(); },
      });
    });
  }

  update(time) {
    // bob gently while moored: one pixel-step every 425 ms (850 ms up and down)
    const bob = this.moving ? 0 : (Math.floor(time / 425) % 2) * 2;
    const h = this.sprite.displayHeight;
    this.sprite.setPosition(Math.round(this.x), Math.round(this.y) - bob).setDepth(this.y + h / 2);
    if (this.moving) {
      // the wake trails behind the stern, 8 frames a second
      const d = this.moving;
      const f = (Math.floor(time / 125) % 4) + 1;
      const sternY = d === 'down' ? this.y - h / 2 + 10 : this.y + h / 2 - 10;
      this.wake.setTexture(`wake_${d}_${f}`).setOrigin(0.5, boatInfo.wakeTip[d]).setPosition(this.x, sternY)
        .setDepth(this.sprite.depth - 1).setVisible(true);
    } else {
      this.wake.setVisible(false);
    }
  }
}

// every frame: move the boat, and show the sail button when the capybara stands at the dock end
export function boatTick(scene, time) {
  scene.boat.update(time);
  let label = null;
  if (scene.playing) {
    const [bx, by] = scene.boat.board;
    const near = Math.hypot(scene.player.x - bx, scene.player.y - by) < BOARD_RANGE;
    const why = scene.cantSail?.();
    if (!near) scene.justLanded = false; // the button waits until you have stepped off the dock once
    if (near && !why && !scene.justLanded) label = ISLANDS[otherIsland(scene.scene.key)].sailLabel;
    if (near && why && !scene.toldCantSail) {
      scene.toldCantSail = true;
      ui.toast(why);
    }
    if (!near) scene.toldCantSail = false;
  }
  if (label !== (scene.sailLabel ?? null)) {
    ui.sail(label);
    scene.sailLabel = label;
  }
}

// leave this island: board, row away, fade, and wake the other island
export function sailAway(scene) {
  if (scene.sailing) return;
  scene.sailing = true;
  scene.playing = false;
  scene.path = null;
  ui.sail(null);
  scene.sailLabel = null;
  ui.arrow(null);
  const p = scene.player;
  const boat = scene.boat;
  const cam = scene.cameras.main;
  const row = () => {
    p.setVisible(false);
    p.shadow.setVisible(false);
    boat.show('capy', 'down');
    scene.camTarget = boat.sprite;
    cam.startFollow(boat.sprite, false, 0.1, 0.1);
    boat.row(TRIP, 1600, 'Sine.easeIn');
    scene.time.delayedCall(1300, () => {
      cam.fadeOut(300, ...WATER);
      cam.once('camerafadeoutcomplete', () => {
        boat.x = boat.home.x;
        boat.y = boat.home.y;
        boat.show('empty', boat.dir);
        scene.camTarget = null;
        scene.sailing = false;
        scene.scene.switch(otherIsland(scene.scene.key), { arriving: true });
      });
    });
  };
  const [bx, by] = boat.board;
  if (Math.hypot(p.x - bx, p.y - by) < BOARD_RANGE * 1.5) {
    row();
  } else {
    // sailing from somewhere else on the island (the win card): hop over to the boat first
    cam.stopFollow();
    scene.tweens.add({ targets: [p, p.shadow], alpha: 0, duration: 250 });
    cam.pan(boat.x, boat.y - 40, 800, 'Sine.easeInOut', false, (c, t) => {
      if (t < 1) return;
      p.setPosition(bx, by);
      p.alpha = 1;
      p.shadow.alpha = 1;
      row();
    });
  }
}

// arrive at this island: row in from the sea, then step onto the dock
export function arrive(scene) {
  scene.playing = false;
  scene.sailing = true;
  scene.path = null;
  const p = scene.player;
  const boat = scene.boat;
  const cam = scene.cameras.main;
  p.setVisible(false);
  p.shadow.setVisible(false);
  boat.show('capy', 'up');
  boat.x = boat.home.x;
  boat.y = boat.home.y + TRIP;
  boat.update(scene.time.now);
  scene.camTarget = boat.sprite;
  scene.fitCamera();
  cam.centerOn(boat.x, boat.y - 60);
  cam.fadeIn(300, ...WATER);
  scene.showHud();
  boat.row(-TRIP, 1600, 'Sine.easeOut').then(() => {
    boat.show('empty', boat.dir);
    p.setPosition(...boat.board);
    p.setVisible(true);
    p.shadow.setVisible(true);
    scene.landed();
    scene.justLanded = true;
    scene.camTarget = null;
    scene.sailing = false;
    scene.playing = true;
    scene.fitCamera();
    scene.onArrive();
  });
}

// hook an island scene up to the boat: arriving on first start, or when woken up by a switch
export function setupBoat(scene, spot, data) {
  scene.boat = new Boat(scene, spot);
  const onWake = (sys, d) => { if (d?.arriving) arrive(scene); else scene.showHud(); };
  scene.events.on('wake', onWake);
  scene.events.once('shutdown', () => scene.events.off('wake', onWake));
  if (data?.arriving) scene.time.delayedCall(0, () => arrive(scene));
}
