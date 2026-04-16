const NODE_W_MIN = 220;
const NODE_W_MAX = 340;
const NODE_H_MIN = 100;
const NODE_H_MAX = 130;

const COLLAPSED_W = 200;
const COLLAPSED_H = 52;

function nodeDims(lines) {
  const l = lines || 0;
  // scale width: 180 at 0 LOC → 300 at 500+ LOC
  const wt = Math.min(l / 500, 1);
  const w = Math.round(NODE_W_MIN + wt * (NODE_W_MAX - NODE_W_MIN));
  // scale height: 80 at 0 LOC → 110 at 500+ LOC
  const ht = Math.min(l / 500, 1);
  const h = Math.round(NODE_H_MIN + ht * (NODE_H_MAX - NODE_H_MIN));
  return { w, h };
}

const PAD_L       = 44;   
const PAD_R       = 44;   
const PAD_TOP     = 58;  
const PAD_BOT     = 40;  

const GAP_X = 56; 
const GAP_Y = 72; 

function gid(folder) {
  return `grp__${folder.replace(/[^a-zA-Z0-9]/g, "_")}`;
}

function parentOf(folder) {
  if (!folder || folder === ".") return null;
  const parts = folder.split("/");
  return parts.length === 1 ? "." : parts.slice(0, -1).join("/");
}

function shortName(folder) {
  if (!folder || folder === ".") return "root";
  return folder.split("/").pop();
}

function buildTree(codeNodes) {
  const tree = new Map();

  function ensure(f) {
    if (tree.has(f)) return;
    tree.set(f, { folder: f, directFiles: [], children: new Set() });
    const p = parentOf(f);
    if (p !== null) {
      ensure(p);
      tree.get(p).children.add(f);
    }
  }

  codeNodes.forEach((n) => {
    const f = n.data?.folder || ".";
    ensure(f);
    tree.get(f).directFiles.push(n.id);
  });

  return tree;
}

function packGrid(items) {
  if (items.length === 0) return { placements: [], contentW: 0, contentH: 0 };

  const n = items.length;
  // Refine column count to be slightly more balanced (1.4 instead of 1.8)
  // to prevent extreme horizontal stretching that forces tiny zoom levels.
  const cols = Math.max(1, Math.ceil(Math.sqrt(n) * 1.4));
  const avgW = items.reduce((s, it) => s + it.w, 0) / n;
  const maxRowW = cols * (avgW + GAP_X);

  let cx = 0, cy = 0, rowH = 0, maxX = 0;
  const placements = [];

  items.forEach((item) => {
    if (cx > 0 && cx + item.w > maxRowW) {
      cx = 0;
      cy += rowH + GAP_Y;
      rowH = 0;
    }
    placements.push({ ...item, x: cx, y: cy });
    maxX = Math.max(maxX, cx + item.w);
    rowH = Math.max(rowH, item.h);
    cx += item.w + GAP_X;
  });

  return {
    placements,
    contentW: maxX,
    contentH: cy + rowH,
  };
}

function layoutFolder(folder, tree, nodeById, colorIdx, collapsedSet) {
  const entry = tree.get(folder);
  const isCollapsed = collapsedSet.has(folder);

  // If collapsed, return compact dimensions — no children emitted
  if (isCollapsed) {
    return {
      w: COLLAPSED_W,
      h: COLLAPSED_H,
      colorIdx,
      collapsed: true,
      emitInto(out, myGroupId) {
        // Don't emit any children
      },
    };
  }

  const childLayouts = [];
  const sortedChildren = Array.from(entry.children).sort();

  sortedChildren.forEach((childFolder, i) => {
    const layout = layoutFolder(childFolder, tree, nodeById, colorIdx + 1 + i, collapsedSet);
    childLayouts.push({ folder: childFolder, layout });
  });

  const items = [];

  entry.directFiles.forEach((nodeId) => {
    const node = nodeById.get(nodeId);
    const lines = node?.data?.lines || 0;
    const { w, h } = nodeDims(lines);
    items.push({ kind: "file", nodeId, w, h });
  });

  childLayouts
    .sort((a, b) => b.layout.h - a.layout.h) 
    .forEach(({ folder: cf, layout }) => {
      items.push({ kind: "group", folder: cf, layout, w: layout.w, h: layout.h });
    });

  const { placements, contentW, contentH } = packGrid(items);

  const totalW = contentW + PAD_L + PAD_R;
  const totalH = contentH + PAD_TOP + PAD_BOT;

  function emitInto(out, myGroupId) {
    placements.forEach((p) => {
      const rx = p.x + PAD_L;
      const ry = p.y + PAD_TOP;

      if (p.kind === "file") {
        const original = nodeById.get(p.nodeId);
        if (!original) return;
        out.push({
          ...original,
          parentId: myGroupId,
          extent: "parent",
          position: { x: rx, y: ry },
          zIndex: 50,
        });

      } else {
        const childFolder = p.folder;
        const childGid = gid(childFolder);
        const childLayout = p.layout;

        out.push({
          id: childGid,
          type: "folderGroup",
          parentId: myGroupId,
          extent: "parent",
          position: { x: rx, y: ry },
          style: { width: childLayout.w, height: childLayout.h },
          data: {
            folder: childFolder,
            label: shortName(childFolder),
            fullPath: `/${childFolder}/`,
            count: countAllFiles(childFolder, tree),
            colorIdx: childLayout.colorIdx,
            collapsed: childLayout.collapsed || false,
          },
          selectable: true,
          draggable: true,
          zIndex: -(colorIdx + 1),
        });

        childLayout.emitInto(out, childGid);
      }
    });
  }

  return { w: totalW, h: totalH, colorIdx, collapsed: false, emitInto };
}

function countAllFiles(folder, tree) {
  const entry = tree.get(folder);
  if (!entry) return 0;
  let n = entry.directFiles.length;
  entry.children.forEach((c) => { n += countAllFiles(c, tree); });
  return n;
}

/**
 * Collect all descendant node IDs (file node IDs) under a folder recursively.
 * Used by GraphCanvas to reroute edges when a folder is collapsed.
 */
export function collectDescendantNodeIds(folder, nodes) {
  const groupId = gid(folder);
  const ids = new Set();
  nodes.forEach((n) => {
    if (n.type === "codeNode") {
      const f = n.data?.folder || ".";
      if (f === folder || f.startsWith(folder + "/")) {
        ids.add(n.id);
      }
    }
  });
  return { groupId, ids };
}

export function applyDagreLayout(nodes, edges, collapsedFolders = new Set()) {
  if (!nodes || nodes.length === 0) return { nodes: [], edges: [] };

  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const tree = buildTree(nodes);

  const allFolders = new Set(tree.keys());
  const roots = Array.from(allFolders)
    .filter((f) => {
      const p = parentOf(f);
      return p === null || !allFolders.has(p);
    })
    .sort();

  const output = [];
  let offsetX = 0;

  roots.forEach((rootFolder) => {
    const layout = layoutFolder(rootFolder, tree, nodeById, 0, collapsedFolders);
    const rootGid = gid(rootFolder);

    output.push({
      id: rootGid,
      type: "folderGroup",
      position: { x: offsetX, y: 0 },
      style: { width: layout.w, height: layout.h },
      data: {
        folder: rootFolder,
        label: shortName(rootFolder),
        fullPath: rootFolder === "." ? "/" : `/${rootFolder}/`,
        count: countAllFiles(rootFolder, tree),
        colorIdx: 0,
        collapsed: layout.collapsed || false,
      },
      selectable: true,
      draggable: true,
      zIndex: -200,
    });

    layout.emitInto(output, rootGid);

    offsetX += layout.w + 160;
  });

  const groups  = output.filter((n) => n.type === "folderGroup");
  const files   = output.filter((n) => n.type !== "folderGroup");

  groups.sort((a, b) => {
    const depA = (a.data?.folder || ".").split("/").length;
    const depB = (b.data?.folder || ".").split("/").length;
    return depA - depB;
  });

  // Build a set of visible node IDs (only the file nodes that were emitted)
  const visibleNodeIds = new Set(files.map((n) => n.id));
  const groupIds = new Set(groups.map((g) => g.id));

  // For collapsed folders, build a mapping: hidden nodeId -> collapsed group id
  const hiddenToGroup = {};
  for (const folder of collapsedFolders) {
    const groupId = gid(folder);
    if (!groupIds.has(groupId)) continue;
    nodes.forEach((n) => {
      if (n.type !== "codeNode") return;
      const f = n.data?.folder || ".";
      if ((f === folder || f.startsWith(folder + "/")) && !visibleNodeIds.has(n.id)) {
        hiddenToGroup[n.id] = groupId;
      }
    });
  }

  // Process edges: reroute edges touching hidden nodes to collapsed group
  const processedEdges = [];
  const seenEdgeKeys = new Set();
  edges.forEach((e) => {
    const src = hiddenToGroup[e.source] || e.source;
    const tgt = hiddenToGroup[e.target] || e.target;
    // Skip self-loops created by collapse and skip edges where both endpoints are hidden inside the same group
    if (src === tgt) return;
    const key = `${src}→${tgt}`;
    if (seenEdgeKeys.has(key)) return;
    seenEdgeKeys.add(key);
    processedEdges.push({
      ...e,
      id: `e_${src}_${tgt}`,
      source: src,
      target: tgt,
    });
  });

  return { nodes: [...groups, ...files], edges: processedEdges };
}