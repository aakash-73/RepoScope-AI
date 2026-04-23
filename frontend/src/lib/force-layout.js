import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY } from "d3-force";

/**
 * Applies a force-directed layout to nodes and edges.
 * Clusters file nodes around their associated category hubs.
 */
export function applyForceLayout(nodes, edges, options = {}) {
  const { width = 1200, height = 800, strength = -300, distance = 100 } = options;

  // Clone nodes to avoid mutating original data
  const simulationNodes = nodes.map((n) => ({
    ...n,
    x: Math.random() * width,
    y: Math.random() * height,
  }));

  const nodeMap = new Map(simulationNodes.map((n) => [n.id, n]));

  const simulationEdges = edges
    .map((e) => ({
      source: nodeMap.get(e.source),
      target: nodeMap.get(e.target),
      relation: e.label || "imports",
    }))
    .filter((e) => e.source && e.target);

  const simulation = forceSimulation(simulationNodes)
    .force("link", forceLink(simulationEdges).id((d) => d.id).distance((d) => {
      // Tighter orbits around hubs, looser between files
      if (d.relation === "belongs_to") return 60;
      if (d.relation === "has_role") return 80;
      return distance * 1.5;
    }).strength(0.6))
    .force("charge", forceManyBody().strength((n) => {
        // Massive repulsion for hubs to create distinct island galaxies
        return n.type === "hubNode" ? -6000 : -150;
    }))
    .force("center", forceCenter(width / 2, height / 2).strength(0.1))
    .force("collide", forceCollide().radius((n) => (n.type === "hubNode" ? 120 : 50)).strength(0.6))
    .force("x", forceX(width / 2).strength(0.05))
    .force("y", forceY(height / 2).strength(0.05));

  // Run simulation with organic swarming force
  for (let i = 0; i < 300; i++) {
    // Pull children orbitally toward their hubs to break any D3 crystal grids
    simulationEdges.forEach(e => {
        const source = typeof e.source === 'object' ? e.source : nodeMap.get(e.source);
        const target = typeof e.target === 'object' ? e.target : nodeMap.get(e.target);
        
        if (source && target && (e.relation === "belongs_to" || e.relation === "has_role")) {
            const hub = target.type === "hubNode" ? target : (source.type === "hubNode" ? source : null);
            const file = source.type === "codeNode" ? source : (target.type === "codeNode" ? target : null);
            if (hub && file) {
                file.vx += (hub.x - file.x) * 0.08;
                file.vy += (hub.y - file.y) * 0.08;
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
    edges: edges, // Return original edges with computed positions for nodes
  };
}
