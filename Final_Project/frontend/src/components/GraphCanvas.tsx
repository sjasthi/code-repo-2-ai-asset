import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useEffect, useRef, useState } from "react";
import type { GraphNodeType } from "../api/types";
import {
  fitGraph,
  focusNode,
  graphStyle,
  highlightMatches,
  matchedNodes,
  runLayout,
  setHiddenTypes,
} from "../graph/interactions";
import { LARGE_GRAPH_NODES, type LayoutName } from "../graph/model";

interface Props {
  elements: ElementDefinition[];
  layout: LayoutName;
  hiddenTypes: GraphNodeType[];
  search: string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onMatchCount?: (count: number) => void;
}

const ZOOM_STEP = 1.3;

export default function GraphCanvas({
  elements,
  layout,
  hiddenTypes,
  search,
  selectedId,
  onSelect,
  onMatchCount,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [cy, setCy] = useState<Core | null>(null);

  // Cytoscape handlers are bound once, so read the latest callbacks via refs.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const onMatchCountRef = useRef(onMatchCount);
  onMatchCountRef.current = onMatchCount;

  // A new instance per data set: the large-graph renderer options can only
  // be set at creation.
  useEffect(() => {
    const nodeCount = elements.filter((element) => element.group === "nodes").length;
    const large = nodeCount > LARGE_GRAPH_NODES;

    const instance = cytoscape({
      container: containerRef.current,
      elements,
      style: graphStyle,
      minZoom: 0.05,
      maxZoom: 4,
      // Draw a snapshot while panning/zooming big graphs.
      textureOnViewport: large,
      hideEdgesOnViewport: large,
      pixelRatio: large ? 1 : "auto",
    });

    instance.on("tap", "node", (event) => onSelectRef.current(event.target.id()));
    instance.on("tap", (event) => {
      if (event.target === instance) onSelectRef.current(null);
    });

    // Dev only: lets you inspect the graph from the browser console.
    if (import.meta.env.DEV) (window as unknown as { cy?: Core }).cy = instance;

    setCy(instance);
    return () => {
      instance.destroy();
      setCy(null);
    };
  }, [elements]);

  useEffect(() => {
    if (!cy) return;
    runLayout(cy, layout);
  }, [cy, layout]);

  useEffect(() => {
    if (cy) setHiddenTypes(cy, hiddenTypes);
  }, [cy, hiddenTypes]);

  useEffect(() => {
    if (!cy) return;
    const count = highlightMatches(cy, search);
    onMatchCountRef.current?.(count);
    if (count > 0) fitGraph(cy, matchedNodes(cy));
  }, [cy, search]);

  useEffect(() => {
    if (!cy) return;
    // Bring the selected node into view without changing the zoom.
    if (focusNode(cy, selectedId) && selectedId && !isInView(cy, selectedId)) {
      cy.center(cy.getElementById(selectedId));
    }
  }, [cy, selectedId]);

  function zoomBy(factor: number) {
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  }

  function savePng() {
    if (!cy) return;
    const link = document.createElement("a");
    link.href = cy.png({ full: true, scale: 2, bg: "#ffffff" });
    link.download = "dependency-graph.png";
    link.click();
  }

  return (
    <div className="graph-canvas">
      <div
        ref={containerRef}
        className="graph-canvas-surface"
        role="img"
        aria-label="Dependency graph. Use the list in the details panel to explore with a keyboard."
      />
      <div className="graph-toolbar" aria-label="Graph view controls">
        <button type="button" onClick={() => zoomBy(ZOOM_STEP)} aria-label="Zoom in" title="Zoom in">
          +
        </button>
        <button type="button" onClick={() => zoomBy(1 / ZOOM_STEP)} aria-label="Zoom out" title="Zoom out">
          −
        </button>
        <button type="button" onClick={() => cy && fitGraph(cy)} title="Fit the whole graph">
          Fit
        </button>
        <button type="button" onClick={() => cy && runLayout(cy, layout)} title="Run the layout again">
          Re-layout
        </button>
        <button type="button" onClick={savePng} title="Download as PNG">
          PNG
        </button>
      </div>
    </div>
  );
}

function isInView(cy: Core, id: string): boolean {
  const box = cy.getElementById(id).renderedBoundingBox();
  return box.x1 >= 0 && box.y1 >= 0 && box.x2 <= cy.width() && box.y2 <= cy.height();
}
