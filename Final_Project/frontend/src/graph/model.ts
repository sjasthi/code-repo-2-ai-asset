import type { ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode, GraphNodeType, GraphResponse } from "../api/types";

export const NODE_TYPES: { type: GraphNodeType; label: string }[] = [
  { type: "file", label: "Files" },
  { type: "class", label: "Classes" },
  { type: "function", label: "Functions" },
  { type: "method", label: "Methods" },
  { type: "variable", label: "Variables" },
  { type: "external", label: "Unresolved calls" },
];

// Colour and shape per type. Shapes keep types apart without relying on colour.
export const NODE_LOOK: Record<GraphNodeType, { color: string; shape: string }> = {
  file: { color: "#0c6b6b", shape: "round-rectangle" },
  class: { color: "#7c3aed", shape: "diamond" },
  function: { color: "#2563eb", shape: "ellipse" },
  method: { color: "#db2777", shape: "ellipse" },
  variable: { color: "#b26a00", shape: "triangle" },
  external: { color: "#8a94a3", shape: "ellipse" },
};

export function toElements(graph: GraphResponse): ElementDefinition[] {
  return [
    ...graph.nodes.map((node) => ({ group: "nodes" as const, data: { ...node } })),
    ...graph.edges.map((edge) => ({ group: "edges" as const, data: { ...edge } })),
  ];
}

export interface NodeDetails {
  node: GraphNode;
  imports: GraphNode[];
  importedBy: GraphNode[];
  contains: GraphNode[];
  calls: GraphNode[];
  definedIn: GraphNode | null;
}

// What the side panel shows about one node, from the loaded graph.
export function describeNode(graph: GraphResponse, id: string): NodeDetails | null {
  const byId = new Map(graph.nodes.map((node) => [node.id, node]));
  const node = byId.get(id);
  if (!node) return null;

  const pick = (edges: GraphEdge[], end: "source" | "target") =>
    edges
      .map((edge) => byId.get(edge[end]))
      .filter((other): other is GraphNode => Boolean(other))
      .sort((a, b) => a.label.localeCompare(b.label));

  const from = (type: GraphEdge["type"]) =>
    graph.edges.filter((edge) => edge.type === type && edge.source === id);
  const to = (type: GraphEdge["type"]) =>
    graph.edges.filter((edge) => edge.type === type && edge.target === id);

  return {
    node,
    imports: pick(from("imports"), "target"),
    importedBy: pick(to("imports"), "source"),
    contains: pick(from("contains"), "target"),
    calls: pick(from("calls"), "target"),
    definedIn: pick(to("contains"), "source")[0] ?? null,
  };
}

export type LayoutName =
  | "auto"
  | "clustered"
  | "cose"
  | "breadthfirst"
  | "concentric"
  | "grid";

export const LAYOUTS: { name: LayoutName; label: string }[] = [
  { name: "auto", label: "Automatic" },
  { name: "clustered", label: "Grouped by file" },
  { name: "cose", label: "Force-directed" },
  { name: "breadthfirst", label: "Hierarchy" },
  { name: "concentric", label: "Most connected in the middle" },
  { name: "grid", label: "Grid" },
];

// Force-directed reads best but gets slow past a few hundred nodes.
export const FORCE_LAYOUT_MAX_NODES = 400;
// Past this, labels only show when zoomed in and panning uses a snapshot.
export const LARGE_GRAPH_NODES = 1500;

export function resolveLayout(name: LayoutName, nodeCount: number): Exclude<LayoutName, "auto"> {
  if (name !== "auto") return name;
  return nodeCount <= FORCE_LAYOUT_MAX_NODES ? "cose" : "clustered";
}
