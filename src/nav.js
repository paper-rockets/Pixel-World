// Where the capybara may stand, and how to walk around things to reach a tapped spot.
const FOOT = 11;   // how wide the capybara's feet are, in island pixels
const CELL = 8;    // size of one pathfinding square

export function inPoly(poly, x, y) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export class Nav {
  // ground(x, y): is this spot walkable ground (grass, path, sand)? blockers: walls on top of it.
  constructor({ width, height, start, ground, blockers = [] }) {
    this.ground = ground;
    this.blockers = blockers;
    this.cols = Math.ceil(width / CELL);
    this.rows = Math.ceil(height / CELL);
    const n = this.cols * this.rows;
    this.open = new Uint8Array(n);
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        this.open[r * this.cols + c] = this.canStand(c * CELL + CELL / 2, r * CELL + CELL / 2) ? 1 : 0;
      }
    }
    // mark every square you can walk to from the start (ignores little cut-off corners)
    this.reach = new Uint8Array(n);
    const first = this.nearestOpen(this.cellAt(start[0], start[1]));
    const stack = [first];
    this.reach[first] = 1;
    while (stack.length) {
      const k = stack.pop();
      const c = k % this.cols;
      const r = (k / this.cols) | 0;
      for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nc = c + dc;
        const nr = r + dr;
        if (nc < 0 || nr < 0 || nc >= this.cols || nr >= this.rows) continue;
        const nk = nr * this.cols + nc;
        if (this.open[nk] && !this.reach[nk]) { this.reach[nk] = 1; stack.push(nk); }
      }
    }
    // reused between searches
    this.g = new Float32Array(n);
    this.from = new Int32Array(n);
    this.state = new Uint8Array(n); // 0 new, 1 open list, 2 done
  }

  canStand(x, y, r = FOOT) {
    const e = r * 0.6; // let feet get close to the grass edge
    const g = this.ground;
    if (!g(x, y) || !g(x - e, y) || !g(x + e, y) || !g(x, y - e) || !g(x, y + e)) return false;
    for (const b of this.blockers) {
      if (b.type === 'rect') {
        if (x > b.x - r && x < b.x + b.w + r && y > b.y - r && y < b.y + b.h + r) return false;
      } else {
        const dx = (x - b.x) / (b.rx + r);
        const dy = (y - b.y) / (b.ry + r);
        if (dx * dx + dy * dy < 1) return false;
      }
    }
    return true;
  }

  clearLine(ax, ay, bx, by) {
    const steps = Math.ceil(Math.hypot(bx - ax, by - ay) / 4);
    for (let i = 1; i <= steps; i++) {
      const t = i / steps;
      if (!this.canStand(ax + (bx - ax) * t, ay + (by - ay) * t)) return false;
    }
    return true;
  }

  // can the capybara get within `range` of this point?
  canReach(x, y, range) {
    const c0 = Math.floor((x - range) / CELL);
    const c1 = Math.floor((x + range) / CELL);
    const r0 = Math.floor((y - range) / CELL);
    const r1 = Math.floor((y + range) / CELL);
    for (let r = Math.max(0, r0); r <= Math.min(this.rows - 1, r1); r++) {
      for (let c = Math.max(0, c0); c <= Math.min(this.cols - 1, c1); c++) {
        if (!this.reach[r * this.cols + c]) continue;
        if (Math.hypot(c * CELL + CELL / 2 - x, r * CELL + CELL / 2 - y) <= range) return true;
      }
    }
    return false;
  }

  cellAt(x, y) {
    const c = Math.min(this.cols - 1, Math.max(0, Math.floor(x / CELL)));
    const r = Math.min(this.rows - 1, Math.max(0, Math.floor(y / CELL)));
    return r * this.cols + c;
  }

  nearestOpen(i, mask = this.open) {
    if (mask[i]) return i;
    const c0 = i % this.cols;
    const r0 = (i / this.cols) | 0;
    for (let rad = 1; rad < 40; rad++) {
      let best = -1;
      let bestD = Infinity;
      for (let dr = -rad; dr <= rad; dr++) {
        for (let dc = -rad; dc <= rad; dc++) {
          if (Math.max(Math.abs(dr), Math.abs(dc)) !== rad) continue;
          const r = r0 + dr;
          const c = c0 + dc;
          if (r < 0 || c < 0 || r >= this.rows || c >= this.cols) continue;
          const k = r * this.cols + c;
          const d = dr * dr + dc * dc;
          if (mask[k] && d < bestD) { best = k; bestD = d; }
        }
      }
      if (best >= 0) return best;
    }
    return -1;
  }

  // Returns a list of {x, y} points to walk through, or null if there is no way there.
  findPath(sx, sy, tx, ty) {
    const cols = this.cols;
    const start = this.nearestOpen(this.cellAt(sx, sy), this.reach);
    const tCell = this.cellAt(tx, ty);
    const goal = this.nearestOpen(tCell, this.reach);
    if (start < 0 || goal < 0) return null;
    const exact = goal === tCell && this.canStand(tx, ty);

    const { g, from, state, open } = this;
    g.fill(Infinity);
    from.fill(-1);
    state.fill(0);
    const gc = goal % cols;
    const gr = (goal / cols) | 0;
    const h = (k) => {
      const dx = Math.abs((k % cols) - gc);
      const dy = Math.abs(((k / cols) | 0) - gr);
      return Math.max(dx, dy) + 0.414 * Math.min(dx, dy);
    };
    // small binary heap of [f, cell]
    const heap = [];
    const push = (f, k) => {
      heap.push([f, k]);
      let i = heap.length - 1;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (heap[p][0] <= heap[i][0]) break;
        [heap[p], heap[i]] = [heap[i], heap[p]];
        i = p;
      }
    };
    const pop = () => {
      const top = heap[0];
      const last = heap.pop();
      if (heap.length) {
        heap[0] = last;
        let i = 0;
        for (;;) {
          const l = i * 2 + 1;
          const r = l + 1;
          let m = i;
          if (l < heap.length && heap[l][0] < heap[m][0]) m = l;
          if (r < heap.length && heap[r][0] < heap[m][0]) m = r;
          if (m === i) break;
          [heap[m], heap[i]] = [heap[i], heap[m]];
          i = m;
        }
      }
      return top;
    };

    g[start] = 0;
    push(h(start), start);
    let found = false;
    while (heap.length) {
      const [, k] = pop();
      if (state[k] === 2) continue;
      state[k] = 2;
      if (k === goal) { found = true; break; }
      const c = k % cols;
      const r = (k / cols) | 0;
      for (let dr = -1; dr <= 1; dr++) {
        for (let dc = -1; dc <= 1; dc++) {
          if (!dr && !dc) continue;
          const nc = c + dc;
          const nr = r + dr;
          if (nc < 0 || nr < 0 || nc >= cols || nr >= this.rows) continue;
          const nk = nr * cols + nc;
          if (!open[nk] || state[nk] === 2) continue;
          if (dr && dc && (!open[r * cols + nc] || !open[nr * cols + c])) continue; // no corner cutting
          const ng = g[k] + (dr && dc ? 1.414 : 1);
          if (ng < g[nk]) {
            g[nk] = ng;
            from[nk] = k;
            push(ng + h(nk), nk);
          }
        }
      }
    }
    if (!found) return null;

    const cells = [];
    for (let k = goal; k !== -1; k = from[k]) cells.push(k);
    cells.reverse();
    const pts = cells.map((k) => ({ x: (k % cols) * CELL + CELL / 2, y: ((k / cols) | 0) * CELL + CELL / 2 }));
    if (exact) pts[pts.length - 1] = { x: tx, y: ty };

    // straighten: skip corners when there is a clear straight line
    const out = [];
    let ax = sx;
    let ay = sy;
    let i = 0;
    while (i < pts.length) {
      let j = pts.length - 1;
      while (j > i && !this.clearLine(ax, ay, pts[j].x, pts[j].y)) j--;
      out.push(pts[j]);
      ax = pts[j].x;
      ay = pts[j].y;
      i = j + 1;
    }
    return out;
  }
}
