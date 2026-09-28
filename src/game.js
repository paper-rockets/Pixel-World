import Phaser from 'phaser';
import './style.css';
import { PlayScene } from './PlayScene.js';
import { SchoolScene } from './school/SchoolScene.js';
import { sailAway } from './boat.js';
import { ui } from './ui.js';

// Both islands live in one game so the boat can row between them.
// first: 'play' (Sunny Meadow, Lost Ducklings) or 'school' (Orange Garden)
export function startGame(first) {
  // Draw at the screen's real sharpness (capped at 2x so older tablets stay smooth).
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  const screenSize = () => [Math.round(window.innerWidth * DPR), Math.round(window.innerHeight * DPR)];
  const [width, height] = screenSize();

  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: 'game',
    width,
    height,
    backgroundColor: '#4cc1e6',
    scale: { mode: Phaser.Scale.NONE, zoom: 1 / DPR },
    scene: first === 'school' ? [SchoolScene, PlayScene] : [PlayScene, SchoolScene],
  });

  window.addEventListener('resize', () => game.scale.resize(...screenSize()));
  if (new URLSearchParams(location.search).has('debug')) window.game = game;

  // whichever island is running right now
  const island = () => game.scene.getScenes(true).find((s) => s.boat) || game.scene.getScene(first);

  ui.init({
    onPlay: () => island().begin(),
    onAgain: () => island().scene.restart({ autoStart: true }),
    onSound: (muted) => { if (game.sound) game.sound.mute = muted; },
    onArrow: () => island().goToGoal(),
    onSail: () => sailAway(island()),
  });
  return game;
}
