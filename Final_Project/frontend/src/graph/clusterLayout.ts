import type { Core, NodeSingular, Position } from "cytoscape";

/**
 * Layout for large graphs: lay out only the files, then put each file's
 * symbols in a tight spiral around it. Running a force layout on thousands
 * of symbol nodes is slow and unreadable; files are usually a few hundred.
 *
 * Nodes that belong to no loaded file (unresolved call targets, functions
 * in files outside the view) go on an outer ring, on the side nearest the
 * files that reference them.
 */

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
const SPIRAL_START = 26; // gap between a file and its first symbol
const SPIRAL_STEP = 10; // grows the spiral so symbols don't overlap
const CLUSTER_GAP = 50;
const RING_SPACING = 22; // between neighbouring nodes on the outer ring
// Above this many files a force layout gets slow; use a grid of clusters.
const FORCE_MAX_FILES = 400;

export function clusterRadius(symbolCount: number): number {
  return SPIRAL_START + SPIRAL_STEP * Math.sqrt(symbolCount);
}

export function clusteredPositions(cy: Core): Record<string, Position> {
  const files = cy.nodes('[type = "file"]');
  const positions: Record<string, Position> = {};
  const members = new Map<string, NodeSingular[]>();
  const placed = new Set<string>();

  files.forEach((file) => {
    const symbols = file.outgoers('edge[type = "contains"]').targets().toArray();
    members.set(file.id(), symbols);
    placed.add(file.id());
    symbols.forEach((symbol) => placed.add(symbol.id()));
  });

  // 1. Files only, each sized as its whole cluster so the layout leaves
  //    room for the symbols around it.
  const fileList = files.toArray();
  const radii = fileList.map((file) => clusterRadius(members.get(file.id())!.length));
  fileList.forEach((file, index) => {
    file.style({ width: radii[index] * 2, height: radii[index] * 2 });
  });

  files
    .union(files.edgesWith(files))
    .layout(
      files.length <= FORCE_MAX_FILES
        ? {
            name: "cose",
            animate: false,
            fit: false,
            randomize: true,
            nodeOverlap: 40,
            nodeRepulsion: () => 400000,
            idealEdgeLength: () => 80,
            gravity: 0.6,
            numIter: 1000,
          }
        : { name: "grid", animate: false, fit: false, avoidOverlap: true },
    )
    .run();

  fileList.forEach((file) => file.removeStyle("width height"));
  const centers = separate(
    fileList.map((file) => ({ ...file.position() })),
    radii,
  );

  fileList.forEach((file, index) => {
    const center = centers[index];
    positions[file.id()] = center;

    // 2. Symbols in a sunflower spiral around their file.
    members.get(file.id())!.forEach((symbol, k) => {
      const radius = SPIRAL_START + SPIRAL_STEP * Math.sqrt(k + 1);
      const angle = k * GOLDEN_ANGLE;
      positions[symbol.id()] = {
        x: center.x + radius * Math.cos(angle),
        y: center.y + radius * Math.sin(angle),
      };
    });
  });

  // 3. Everything else on an outer ring, ordered by where it's referenced.
  const loose = cy.nodes().toArray().filter((node) => !placed.has(node.id()));
  if (loose.length > 0) {
    const inner = Object.values(positions);
    const center = inner.length ? average(inner) : { x: 0, y: 0 };
    const reach = inner.reduce(
      (max, p) => Math.max(max, Math.hypot(p.x - center.x, p.y - center.y)),
      0,
    );
    const ring = Math.max(reach + 160, (loose.length * RING_SPACING) / (2 * Math.PI));

    const byAngle = loose
      .map((node) => {
        const anchors = node
          .incomers("node")
          .map((other) => positions[other.id()])
          .filter(Boolean);
        const anchor = anchors.length ? average(anchors) : center;
        return { node, angle: Math.atan2(anchor.y - center.y, anchor.x - center.x) };
      })
      .sort((a, b) => a.angle - b.angle);

    byAngle.forEach(({ node }, index) => {
      const angle = (index / byAngle.length) * 2 * Math.PI - Math.PI;
      positions[node.id()] = {
        x: center.x + ring * Math.cos(angle),
        y: center.y + ring * Math.sin(angle),
      };
    });
  }

  return positions;
}

/**
 * Push overlapping circles apart, pair by pair, until none overlap. The
 * force layout gets close; this cleans up what it leaves.
 */
export function separate(centers: Position[], radii: number[], maxPasses = 200): Position[] {
  const result = centers.map((p) => ({ ...p }));

  for (let pass = 0; pass < maxPasses; pass++) {
    let moved = false;

    for (let i = 0; i < result.length; i++) {
      for (let j = i + 1; j < result.length; j++) {
        let dx = result[j].x - result[i].x;
        let dy = result[j].y - result[i].y;
        let distance = Math.hypot(dx, dy);
        const needed = radii[i] + radii[j] + CLUSTER_GAP;
        if (distance >= needed) continue;

        if (distance < 1e-6) {
          // Same spot: pick a direction that differs per pair.
          const angle = (i * 7 + j * 13) % 360;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          distance = 1;
        }

        const push = (needed - distance) / 2 + 0.01;
        const ux = dx / distance;
        const uy = dy / distance;
        result[i].x -= ux * push;
        result[i].y -= uy * push;
        result[j].x += ux * push;
        result[j].y += uy * push;
        moved = true;
      }
    }

    if (!moved) break;
  }

  return result;
}

function average(points: Position[]): Position {
  const sum = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
  return { x: sum.x / points.length, y: sum.y / points.length };
}
