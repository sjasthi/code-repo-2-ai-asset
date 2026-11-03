import type { CollectionArgument, Core, LayoutOptions, StylesheetJson } from "cytoscape";
import type { GraphNodeType } from "../api/types";
import { clusteredPositions } from "./clusterLayout";
import { NODE_LOOK, resolveLayout, type LayoutName } from "./model";

// Each kind of highlight has its own class so search and selection can
// both be active without undoing each other.
const FOCUS = "focus";
const NEIGHBOUR = "neighbour";
const OUTGOING = "outgoing";
const INCOMING = "incoming";
const FOCUS_DIM = "focus-dim";
const MATCH = "match";
const SEARCH_DIM = "search-dim";
const HIDDEN = "hidden";

export const graphStyle: StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 10,
      "font-family": "IBM Plex Sans, system-ui, sans-serif",
      color: "#1b2430",
      "text-valign": "bottom",
      "text-margin-y": 3,
      "text-wrap": "ellipsis",
      "text-max-width": "120px",
      // Labels disappear when they would be too small to read, which also
      // keeps large graphs fast.
      "min-zoomed-font-size": 7,
      width: 14,
      height: 14,
      "border-width": 0,
    },
  },
  ...Object.entries(NODE_LOOK).map(([type, look]) => ({
    selector: `node[type = "${type}"]`,
    style: { "background-color": look.color, shape: look.shape as never },
  })),
  { selector: 'node[type = "file"]', style: { width: 22, height: 16, "font-size": 11 } },
  { selector: 'node[type = "method"]', style: { width: 10, height: 10 } },
  {
    selector: 'node[type = "external"]',
    style: {
      "background-opacity": 0,
      "border-width": 1.5,
      "border-color": NODE_LOOK.external.color,
      color: "#566274",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.2,
      "curve-style": "bezier",
      "line-color": "#9aa5b4",
      "target-arrow-color": "#9aa5b4",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.8,
    },
  },
  { selector: 'edge[type = "imports"]', style: { width: 1.6, "line-color": "#566274", "target-arrow-color": "#566274" } },
  { selector: 'edge[type = "contains"]', style: { "line-style": "dashed", "line-color": "#c3cbd5", "target-arrow-shape": "none" } },
  { selector: 'edge[type = "calls"]', style: { "line-style": "dotted", "line-color": "#2563eb", "target-arrow-color": "#2563eb" } },

  { selector: `.${MATCH}`, style: { "border-width": 3, "border-color": "#f59e0b", "z-index": 20, "font-weight": "bold" } },
  { selector: `.${FOCUS}`, style: { "border-width": 3, "border-color": "#1b2430", "z-index": 30, "font-weight": "bold", "font-size": 12 } },
  { selector: `edge.${OUTGOING}[type != "contains"]`, style: { width: 2.5, "line-color": "#0c6b6b", "target-arrow-color": "#0c6b6b", "z-index": 25 } },
  { selector: `edge.${INCOMING}[type != "contains"]`, style: { width: 2.5, "line-color": "#c2410c", "target-arrow-color": "#c2410c", "z-index": 25 } },
  { selector: `.${FOCUS_DIM}, .${SEARCH_DIM}`, style: { opacity: 0.12 } },
  { selector: `.${HIDDEN}`, style: { display: "none" } },
];

export function clearFocus(cy: Core) {
  cy.elements().removeClass([FOCUS, NEIGHBOUR, OUTGOING, INCOMING, FOCUS_DIM].join(" "));
}

/**
 * Highlight a node, what it points to (outgoing) and what points to it
 * (incoming); fade everything else. Returns false if the node isn't loaded.
 */
export function focusNode(cy: Core, id: string | null): boolean {
  clearFocus(cy);
  if (!id) return false;

  const node = cy.getElementById(id);
  if (node.empty()) return false;

  cy.elements().addClass(FOCUS_DIM);
  node.closedNeighborhood().removeClass(FOCUS_DIM).addClass(NEIGHBOUR);
  node.removeClass(NEIGHBOUR).addClass(FOCUS);
  node.outgoers("edge").addClass(OUTGOING);
  node.incomers("edge").addClass(INCOMING);
  return true;
}

/**
 * Mark nodes whose name or path contains the query and fade the rest.
 * Returns how many matched; an empty query clears the highlight.
 */
export function highlightMatches(cy: Core, query: string): number {
  cy.elements().removeClass(`${MATCH} ${SEARCH_DIM}`);

  const q = query.trim().toLowerCase();
  if (!q) return 0;

  const matches = cy.nodes().filter((node) => {
    const label = String(node.data("label") ?? "").toLowerCase();
    const path = String(node.data("path") ?? "").toLowerCase();
    return label.includes(q) || path.includes(q);
  });

  if (matches.nonempty()) {
    cy.elements().addClass(SEARCH_DIM);
    matches.removeClass(SEARCH_DIM).addClass(MATCH);
    // Keep edges between matches readable.
    matches.edgesWith(matches).removeClass(SEARCH_DIM);
  }

  return matches.length;
}

export function matchedNodes(cy: Core) {
  return cy.nodes(`.${MATCH}`);
}

export function setHiddenTypes(cy: Core, hidden: GraphNodeType[]) {
  cy.batch(() => {
    cy.nodes().forEach((node) => {
      node.toggleClass(HIDDEN, hidden.includes(node.data("type")));
    });
  });
}

// Fitting a small graph would blow it up; past this zoom, labels get huge.
export const MAX_FIT_ZOOM = 1.5;

export function runLayout(cy: Core, name: LayoutName) {
  cy.layout(layoutOptions(cy, name)).run();
  fitGraph(cy);
}

export function fitGraph(cy: Core, elements?: CollectionArgument) {
  cy.fit(elements, 40);
  if (cy.zoom() > MAX_FIT_ZOOM) {
    cy.zoom(MAX_FIT_ZOOM);
    cy.center(elements);
  }
}

export function layoutOptions(cy: Core, name: LayoutName): LayoutOptions {
  const nodeCount = cy.nodes().length;
  const resolved = resolveLayout(name, nodeCount);
  const common = { animate: false, fit: true, padding: 30 };

  switch (resolved) {
    case "clustered":
      return { ...common, name: "preset", positions: clusteredPositions(cy) };
    case "cose":
      return {
        ...common,
        name: "cose",
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: () => 60000,
        nodeOverlap: 20,
        idealEdgeLength: () => 110,
        gravity: 0.3,
        numIter: nodeCount > 200 ? 500 : 1500,
        randomize: true,
      };
    case "breadthfirst":
      return { ...common, name: "breadthfirst", directed: true, spacingFactor: 1.3, nodeDimensionsIncludeLabels: true };
    case "concentric":
      return {
        ...common,
        name: "concentric",
        concentric: (node) => node.degree(false),
        levelWidth: () => 2,
        minNodeSpacing: 12,
      };
    case "grid":
      return { ...common, name: "grid", avoidOverlap: true };
  }
}
