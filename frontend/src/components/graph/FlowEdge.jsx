import React, { memo } from "react";
import { BaseEdge, getSmoothStepPath, getStraightPath } from "@xyflow/react";

const CHAIN_CONFIG = {
  "direct-upstream": { color: "#F59E0B", opacity: 0.95, strokeW: 2.2, showDots: true, glow: true },
  "direct-downstream": { color: "#4ADE80", opacity: 0.95, strokeW: 2.2, showDots: true, glow: true },
  "upstream": { color: "#F59E0B", opacity: 0.45, strokeW: 1.4, showDots: false, glow: false },
  "downstream": { color: "#4ADE80", opacity: 0.45, strokeW: 1.4, showDots: false, glow: false },
};

function FlowEdge({
  id,
  sourceX, sourceY,
  targetX, targetY,
  sourcePosition, targetPosition, // explicitly unpack these in the props
  style = {},
  data,
}) {
  const baseColor = style?.stroke || "#B6FF3B";
  const isCircular = data?.is_circular ?? false;
  const isCross = data?.cross_folder ?? false;
  const chainRole = data?.chainRole ?? null;
  const hovering = data?.hovering ?? false;
  const coupling = data?.coupling_score ?? 0;

  let color, opacity, strokeW, showDots, showGlow, dashArray;

  if (isCircular) {
    const unrelated = hovering && chainRole === null;
    color = "#FF4500";
    opacity = unrelated ? 0.25 : 0.9;
    strokeW = unrelated ? 1.5 : 2.5;
    showDots = !unrelated;
    showGlow = !unrelated;
    dashArray = "7 4";
  } else if (hovering && chainRole === null) {
    color = "#374151";
    opacity = 0.08;
    strokeW = 1;
    showDots = false;
    showGlow = false;
    dashArray = undefined;
  } else if (chainRole && CHAIN_CONFIG[chainRole]) {
    const cfg = CHAIN_CONFIG[chainRole];
    color = cfg.color;
    opacity = cfg.opacity;
    strokeW = cfg.strokeW;
    showDots = cfg.showDots;
    showGlow = cfg.glow;
    dashArray = undefined;
  } else if (coupling >= 2) {
    // Over-coupled edge: thicker, warm warning color
    color = coupling >= 3 ? "#EF4444" : "#F59E0B";
    opacity = 0.8;
    strokeW = Math.min(2 + coupling, 5);
    showDots = true;
    showGlow = true;
    dashArray = undefined;
  } else {
    color = baseColor;
    const isPending = data?.is_pending ?? false;
    opacity = isPending ? 0.08 : (isCross ? 0.35 : 0.55);
    strokeW = isPending ? 0.8 : (isCross ? 1.2 : 1.5);
    showDots = !isPending;
    showGlow = false;
    dashArray = isPending ? "4 4" : undefined;
  }

  const isSemantic = data?.isSemantic === true;
  
  const dx = targetX - sourceX;
  const dy = targetY - sourceY;

  let edgePath;
  if (isSemantic) {
    // Override structural edge colors with pure visibility for semantic view
    color = "#FFFFFF"; 
    opacity = hovering ? 1 : 0.85;
    strokeW = hovering ? 2 : 1;
    showGlow = false;
    showDots = false;
    dashArray = undefined;

    // Use React Flow's native utility for computing the straight path safely
    const [straightPath] = getStraightPath({
      sourceX, sourceY, targetX, targetY
    });
    edgePath = straightPath;
  } else {
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);

    let srcPos, tgtPos;
    if (absDy > absDx * 1.2) {
      srcPos = dy > 0 ? "bottom" : "top";
      tgtPos = dy > 0 ? "top" : "bottom";
    } else if (absDx > absDy * 1.2) {
      srcPos = dx > 0 ? "right" : "left";
      tgtPos = dx > 0 ? "left" : "right";
    } else {
      if (dy > 0) {
        srcPos = absDx > absDy ? (dx > 0 ? "right" : "left") : "bottom";
        tgtPos = absDx > absDy ? (dx > 0 ? "left" : "right") : "top";
      } else {
        srcPos = absDx > absDy ? (dx > 0 ? "right" : "left") : "top";
        tgtPos = absDx > absDy ? (dx > 0 ? "left" : "right") : "bottom";
      }
    }

    const borderRadius = isCross ? 20 : 10;
    const offset = isCross ? 60 : 30;

    const [stepPath] = getSmoothStepPath({
      sourceX, sourceY, sourcePosition: srcPos,
      targetX, targetY, targetPosition: tgtPos,
      borderRadius, offset,
    });
    edgePath = stepPath;
  }

  const len = Math.sqrt(dx * dx + dy * dy);
  const duration = Math.min(2.8, Math.max(0.5, len / 180));

  const markerId = `arr_${id}`;
  const pathId = `fp_${id}`;
  
  if (isSemantic) {
    color = "#FFFFFF"; // Pure white to guarantee peak visibility
    opacity = hovering ? 1 : 0.85;
    strokeW = hovering ? 2 : 1;
    showGlow = false; // No neon glow for the clean cyber-architecture look
    showDots = false; // No moving dots to reduce noise
  }

  return (
    <>
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 10 10"
          refX="9" refY="5"
          markerWidth="5" markerHeight="5"
          orient="auto"
        >
          <path d="M0,0 L10,5 L0,10 z" fill={color} opacity={opacity > 0.3 ? 0.9 : 0.15} />
        </marker>

        <path id={pathId} d={edgePath} fill="none" stroke="none" />
      </defs>

      {showGlow && (
        <path
          d={edgePath}
          fill="none"
          stroke={color}
          strokeWidth={strokeW + 8}
          strokeOpacity={0.15}
          style={{ pointerEvents: "none" }}
        />
      )}

      <BaseEdge
        path={edgePath}
        id={id}
        markerEnd={`url(#${markerId})`}
        style={{
          stroke: color,
          strokeWidth: strokeW,
          opacity: opacity,
          strokeDasharray: dashArray,
          transition: "stroke 0.15s ease, opacity 0.15s ease, stroke-width 0.15s ease"
        }}
      />

      {showDots && (
        <>
          <circle r={3.2} fill={color} opacity={0.95} style={{ pointerEvents: "none" }}>
            <animateMotion dur={`${duration}s`} repeatCount="indefinite">
              <mpath href={`#${pathId}`} xlinkHref={`#${pathId}`} />
            </animateMotion>
          </circle>
          <circle r={2} fill={color} opacity={0.55} style={{ pointerEvents: "none" }}>
            <animateMotion dur={`${duration}s`} repeatCount="indefinite" begin={`${-(duration / 2)}s`}>
              <mpath href={`#${pathId}`} xlinkHref={`#${pathId}`} />
            </animateMotion>
          </circle>
        </>
      )}
    </>
  );
}

export default memo(FlowEdge);