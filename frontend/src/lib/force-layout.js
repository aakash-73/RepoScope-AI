import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY } from "d3-force";

/**
 * Applies a force-directed layout to nodes and edges.
 * Clusters file nodes around their associated category hubs.
 *
 * @param {object[]} nodes  - ReactFlow node objects.
 * @param {object[]} edges  - ReactFlow edge objects.
 * @param {object}   options
 * @param {number}   options.width            - Canvas width (default 1400).
 * @param {number}   options.height           - Canvas height (default 900).
 * @param {object}   options.existingPositions - Map of { [nodeId]: { x, y } }.
 *   When provided, those nodes are seeded at their current positions so they
 *   barely move, while brand-new nodes settle naturally around their hubs.
 *   Pass an empty object (the default) for a full fresh layout.
 */
export function applyForceLayout(nodes, edges, options = {}) {
  const {
    width = 1400,
    height = 900,
    existingPositions = {},
  } = options;

  const isIncremental = Object.keys(existingPositions).length > 0;

  // Clone nodes, seeding from existingPositions where available so settled
  // nodes stay roughly in place during incremental updates.
  const simulationNodes = nodes.map((n) => {
    const saved = existingPositions[n.id];
    return {
      ...n,
      x: saved ? saved.x : (n.type === "hubNode"
        ? width  * 0.2 + Math.random() * width  * 0.6
        : Math.random() * width),
      y: saved ? saved.y : (n.type === "hubNode"
        ? height * 0.2 + Math.random() * height * 0.6
        : Math.random() * height),
    };
  });

  const nodeMap = new Map(simulationNodes.map((n) => [n.id, n]));

  const simulationEdges = edges
    .map((e) => ({
      source: nodeMap.get(e.source),
      target: nodeMap.get(e.target),
      relation: e.label || "imports",
    }))
    .filter((e) => e.source && e.target);

  const simulation = forceSimulation(simulationNodes)
    .force("link", forceLink(simulationEdges)
      .id((d) => d.id)
      .distance((d) => {
        // Tighter orbits around hubs, looser between files
        if (d.relation === "belongs_to") return 90;
        if (d.relation === "has_role")   return 110;
        return 200;
      })
      .strength(0.7)
    )
    .force("charge", forceManyBody().strength((n) => {
      // Massive repulsion for hubs → distinct island galaxies
      return n.type === "hubNode" ? -9000 : -300;
    }))
    .force("center", forceCenter(width / 2, height / 2).strength(0.07))
    // ── Key fix: larger radii + multiple iterations per tick prevent overlaps ──
    .force("collide", forceCollide()
      .radius((n) => (n.type === "hubNode" ? 160 : 85))
      .strength(0.95)
      .iterations(4)   // resolve multi-body pile-ups each tick
    )
    .force("x", forceX(width  / 2).strength(0.03))
    .force("y", forceY(height / 2).strength(0.03));

  // Fresh layout needs more ticks to fully untangle; incremental needs far
  // fewer because most nodes are already in good positions.
  const TICKS = isIncremental ? 180 : 520;

  for (let i = 0; i < TICKS; i++) {
    // Pull file-nodes orbitally toward their hub each tick for galaxy clustering
    simulationEdges.forEach((e) => {
      const source = typeof e.source === "object" ? e.source : nodeMap.get(e.source);
      const target = typeof e.target === "object" ? e.target : nodeMap.get(e.target);

      if (source && target && (e.relation === "belongs_to" || e.relation === "has_role")) {
        const hub  = target.type === "hubNode"  ? target  : (source.type === "hubNode"  ? source  : null);
        const file = source.type === "codeNode" ? source  : (target.type === "codeNode" ? target  : null);
        if (hub && file) {
          // Weaker pull for already-placed nodes → they don't jump across the canvas
          const pull = existingPositions[file.id] ? 0.02 : 0.07;
          file.vx += (hub.x - file.x) * pull;
          file.vy += (hub.y - file.y) * pull;
        }
      }
    });
    simulation.tick();
  }

  return {
    nodes: simulationNodes.map((n) => ({
      ...n,
      position: { x: n.x, y: n.y },
    })),
    edges, // Return original edges (React Flow manages their paths)
  };
}
