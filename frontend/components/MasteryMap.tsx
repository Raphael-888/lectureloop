"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  MarkerType,
  Position,
  ReactFlow,
  useNodesState,
  type Edge,
  type Node,
} from "@xyflow/react";
import type { Concept, Mastery, MasteryLabel } from "@/lib/types";

export const LABEL_TEXT: Record<MasteryLabel, string> = {
  mastered: "Mastered",
  confused: "Confused",
  not_mastered: "Not mastered",
  untested: "Untested",
};

const COLORS: Record<MasteryLabel, { bg: string; border: string; text: string }> = {
  mastered: { bg: "#e7f6ec", border: "#2f9e5b", text: "#14532d" },
  confused: { bg: "#fff4dc", border: "#d99a0b", text: "#713f12" },
  not_mastered: { bg: "#fde8e8", border: "#d64545", text: "#7f1d1d" },
  untested: { bg: "#f3f4f6", border: "#b6bcc6", text: "#374151" },
};

const COL_WIDTH = 240;
const ROW_HEIGHT = 92;
const NODE_WIDTH = 200;
const NODE_HEIGHT = 70;

// Column = how many prerequisite levels sit below the concept (left = foundations).
function computeDepths(concepts: Concept[]): Map<string, number> {
  const byId = new Map(concepts.map((c) => [c.id, c]));
  const memo = new Map<string, number>();
  const visit = (id: string): number => {
    const cached = memo.get(id);
    if (cached !== undefined) return cached;
    memo.set(id, 0); // guards against cycles in bad data
    const pre = (byId.get(id)?.prerequisites ?? []).filter((p) => byId.has(p));
    const d = pre.length ? 1 + Math.max(...pre.map(visit)) : 0;
    memo.set(id, d);
    return d;
  };
  concepts.forEach((c) => visit(c.id));
  return memo;
}

interface Props {
  concepts: Concept[];
  mastery: Record<string, Mastery>;
  activeConceptId?: string;
}

export default function MasteryMap({ concepts, mastery, activeConceptId }: Props) {
  const layout = useMemo(() => {
    const depths = computeDepths(concepts);
    const columnSize: Record<number, number> = {};
    concepts.forEach((c) => {
      const d = depths.get(c.id) ?? 0;
      columnSize[d] = (columnSize[d] ?? 0) + 1;
    });
    const rowUsed: Record<number, number> = {};

    const nodes: Node[] = concepts.map((c) => {
      const d = depths.get(c.id) ?? 0;
      const row = rowUsed[d] ?? 0;
      rowUsed[d] = row + 1;
      const m = mastery[c.id];
      const label = m?.label ?? "untested";
      const color = COLORS[label];
      const active = c.id === activeConceptId;
      return {
        id: c.id,
        position: { x: d * COL_WIDTH, y: (row - (columnSize[d] - 1) / 2) * ROW_HEIGHT },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
        draggable: false,
        connectable: false,
        data: {
          label: (
            <div className="map-node">
              <div className="map-node-name">{c.name}</div>
              <div className="map-node-meta">
                {LABEL_TEXT[label]}
                {m && label !== "untested" ? ` · ${Math.round(m.p_mastery * 100)}%` : ""}
              </div>
            </div>
          ),
        },
        style: {
          padding: 8,
          overflow: "hidden",
          borderRadius: 10,
          background: color.bg,
          color: color.text,
          border: active ? "3px solid #2563eb" : `1.5px solid ${color.border}`,
          boxShadow: active ? "0 0 0 5px rgba(37, 99, 235, 0.18)" : "none",
          transition: "background 0.4s, border-color 0.4s",
        },
      };
    });

    const edges: Edge[] = concepts.flatMap((c) =>
      c.prerequisites
        .filter((p) => depths.has(p))
        .map((p) => ({
          id: `${p}->${c.id}`,
          source: p,
          target: c.id,
          markerEnd: { type: MarkerType.ArrowClosed, color: "#9aa3af" },
          style: { stroke: "#9aa3af" },
        })),
    );
    return { nodes, edges };
  }, [concepts, mastery, activeConceptId]);

  // React Flow measures nodes and reports the sizes through onNodesChange,
  // so nodes live in state. On updates we keep each node's measured size
  // and only swap in the new colors, labels and positions.
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(layout.nodes);
  useEffect(() => {
    setNodes((prev) => {
      const prevById = new Map(prev.map((n) => [n.id, n]));
      return layout.nodes.map((n) => {
        const old = prevById.get(n.id);
        return old ? { ...old, position: n.position, data: n.data, style: n.style } : n;
      });
    });
  }, [layout, setNodes]);

  return (
    <div className="map-wrap">
      <ReactFlow
        nodes={nodes}
        edges={layout.edges}
        onNodesChange={onNodesChange}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnScroll
        minZoom={0.2}
      >
        <Background gap={20} color="#e5e7eb" />
      </ReactFlow>
      <div className="map-legend">
        {(Object.keys(COLORS) as MasteryLabel[]).map((l) => (
          <span key={l}>
            <i style={{ background: COLORS[l].bg, borderColor: COLORS[l].border }} />
            {LABEL_TEXT[l]}
          </span>
        ))}
        <span className="muted">Arrow: prerequisite → concept</span>
      </div>
    </div>
  );
}
