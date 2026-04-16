import React, { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { ChevronDown, ChevronRight, FolderOpen, FolderClosed } from "lucide-react";

const PALETTE = [
    { border: "rgba(182,255,59,0.35)", label: "rgba(182,255,59,0.8)", glow: "rgba(182,255,59,0.08)" }, // moss
    { border: "rgba(99,179,237,0.35)", label: "rgba(99,179,237,0.8)", glow: "rgba(99,179,237,0.08)" }, // sky
    { border: "rgba(246,173,85,0.35)", label: "rgba(246,173,85,0.8)", glow: "rgba(246,173,85,0.08)" }, // amber
    { border: "rgba(154,117,255,0.35)", label: "rgba(154,117,255,0.8)", glow: "rgba(154,117,255,0.08)" }, // violet
    { border: "rgba(252,129,129,0.35)", label: "rgba(252,129,129,0.8)", glow: "rgba(252,129,129,0.08)" }, // rose
    { border: "rgba(72,212,170,0.35)", label: "rgba(72,212,170,0.8)", glow: "rgba(72,212,170,0.08)" }, // teal
];

function FolderGroup({ data, selected }) {
    const color = PALETTE[data.colorIdx % PALETTE.length];
    const collapsed = data.collapsed || false;
    const FolderIcon = collapsed ? FolderClosed : FolderOpen;
    const ChevronIcon = collapsed ? ChevronRight : ChevronDown;

    return (
        <div
            style={{
                width: "100%",
                height: "100%",
                borderRadius: 16,
                background: selected
                    ? "rgba(255,255,255,0.07)"
                    : collapsed
                    ? "rgba(255,255,255,0.05)"
                    : "rgba(255,255,255,0.03)",
                border: `1.5px ${collapsed ? "solid" : "dashed"} ${color.border}`,
                boxShadow: collapsed
                    ? `inset 0 0 20px ${color.glow}, 0 0 12px ${color.glow}, 0 0 0 1px rgba(255,255,255,0.04)`
                    : `inset 0 0 40px ${color.glow}, 0 0 0 1px rgba(255,255,255,0.04)`,
                position: "relative",
                cursor: "grab",
                transition: "all 0.2s ease",
                pointerEvents: "none",
            }}
        >
            <div
                style={{
                    position: "absolute",
                    top: 10,
                    left: 12,
                    right: 12,
                    height: 34,
                    borderRadius: 8,
                    background: `rgba(255,255,255,0.06)`,
                    border: `1px solid ${color.border}`,
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    paddingLeft: 8,
                    paddingRight: 8,
                    pointerEvents: "all",
                    cursor: "pointer",
                    userSelect: "none",
                }}
                className="nodrag"
                onClick={(e) => {
                    e.stopPropagation();
                    data.onToggleCollapse?.(data.folder);
                }}
                title={collapsed ? "Expand folder" : "Collapse folder"}
            >
                {/* Collapse/Expand chevron */}
                <ChevronIcon
                    size={14}
                    style={{ color: color.label, opacity: 0.9, flexShrink: 0 }}
                />

                {/* Folder icon */}
                <FolderIcon
                    size={13}
                    style={{ color: color.label, opacity: 0.7, flexShrink: 0 }}
                />

                {/* Folder name */}
                <span
                    style={{
                        fontSize: 13,
                        fontFamily: "'JetBrains Mono', 'Fira Mono', monospace",
                        fontWeight: 700,
                        color: color.label,
                        letterSpacing: "0.04em",
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                    }}
                >
                    {data.label}
                </span>

                {/* File count badge */}
                <span
                    style={{
                        fontSize: 11,
                        fontFamily: "monospace",
                        color: color.label,
                        opacity: 0.6,
                        background: "rgba(255,255,255,0.08)",
                        borderRadius: 4,
                        padding: "1px 5px",
                        whiteSpace: "nowrap",
                    }}
                >
                    {data.count} {data.count === 1 ? "file" : "files"}
                </span>
            </div>

            {/* Bottom path label — only show when expanded */}
            {!collapsed && (
                <div
                    style={{
                        position: "absolute",
                        bottom: 7,
                        right: 12,
                        fontSize: 9,
                        fontFamily: "monospace",
                        color: color.label,
                        opacity: 0.3,
                        pointerEvents: "none",
                        userSelect: "none",
                        whiteSpace: "nowrap",
                    }}
                >
                    {data.fullPath}
                </div>
            )}

            {/* Hidden handles so React Flow can attach edges to collapsed groups */}
            {collapsed && (
                <>
                    <Handle type="target" position={Position.Top} id="t"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="target" position={Position.Bottom} id="b-in"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="target" position={Position.Left} id="l"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="target" position={Position.Right} id="r-in"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="source" position={Position.Bottom} id="b"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="source" position={Position.Top} id="t-out"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="source" position={Position.Left} id="l-out"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                    <Handle type="source" position={Position.Right} id="r"
                        style={{ opacity: 0, width: 1, height: 1, pointerEvents: "none" }} />
                </>
            )}
        </div>
    );
}

export default memo(FolderGroup);