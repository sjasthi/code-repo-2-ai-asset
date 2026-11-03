import cytoscape from "cytoscape";
import { describe, expect, it } from "vitest";
import type { GraphResponse } from "../api/types";
import { focusNode, highlightMatches, layoutOptions, setHiddenTypes } from "./interactions";
import { describeNode, resolveLayout, toElements } from "./model";

// app.py -> lib/helpers.py -> lib/db.py; helpers.py defines helper().
const GRAPH: GraphResponse = {
  nodes: [
    { id: "file:app.py", type: "file", label: "app.py", path: "app.py" },
    { id: "file:lib/helpers.py", type: "file", label: "helpers.py", path: "lib/helpers.py" },
    { id: "file:lib/db.py", type: "file", label: "db.py", path: "lib/db.py" },
    { id: "s1", type: "function", label: "helper", path: "lib/helpers.py", line: 3 },
  ],
  edges: [
    { id: "e1", source: "file:app.py", target: "file:lib/helpers.py", type: "imports" },
    { id: "e2", source: "file:lib/helpers.py", target: "file:lib/db.py", type: "imports" },
    { id: "e3", source: "file:lib/helpers.py", target: "s1", type: "contains" },
    { id: "e4", source: "file:app.py", target: "s1", type: "calls" },
  ],
  files: 3,
  total_files: 3,
  truncated: false,
};

function headless() {
  return cytoscape({ headless: true, elements: toElements(GRAPH) });
}

describe("toElements", () => {
  it("turns nodes and edges into Cytoscape elements", () => {
    const elements = toElements(GRAPH);

    expect(elements.filter((e) => e.group === "nodes")).toHaveLength(4);
    expect(elements.find((e) => e.data.id === "e1")).toEqual({
      group: "edges",
      data: GRAPH.edges[0],
    });
  });
});

describe("describeNode", () => {
  it("lists imports, importers and definitions for a file", () => {
    const details = describeNode(GRAPH, "file:lib/helpers.py")!;

    expect(details.imports.map((n) => n.label)).toEqual(["db.py"]);
    expect(details.importedBy.map((n) => n.label)).toEqual(["app.py"]);
    expect(details.contains.map((n) => n.label)).toEqual(["helper"]);
    expect(details.definedIn).toBeNull();
  });

  it("finds the file a symbol is defined in", () => {
    expect(describeNode(GRAPH, "s1")!.definedIn?.path).toBe("lib/helpers.py");
  });

  it("returns null for a node that isn't loaded", () => {
    expect(describeNode(GRAPH, "nope")).toBeNull();
  });
});

describe("focusNode", () => {
  it("highlights the node and its direct neighbours, fading the rest", () => {
    const cy = headless();

    expect(focusNode(cy, "file:lib/helpers.py")).toBe(true);

    expect(cy.$id("file:lib/helpers.py").hasClass("focus")).toBe(true);
    expect(cy.$id("file:app.py").hasClass("focus-dim")).toBe(false);
    expect(cy.$id("file:lib/db.py").hasClass("focus-dim")).toBe(false);
    // Not adjacent to helpers.py.
    expect(cy.$id("e4").hasClass("focus-dim")).toBe(true);

    expect(cy.$id("e2").hasClass("outgoing")).toBe(true);
    expect(cy.$id("e1").hasClass("incoming")).toBe(true);
  });

  it("clears the highlight when nothing is selected", () => {
    const cy = headless();
    focusNode(cy, "file:app.py");

    expect(focusNode(cy, null)).toBe(false);
    expect(cy.$(".focus, .focus-dim, .outgoing, .incoming")).toHaveLength(0);
  });
});

describe("highlightMatches", () => {
  it("matches names and paths case-insensitively", () => {
    const cy = headless();

    expect(highlightMatches(cy, "LIB/")).toBe(3); // two files + helper's path
    expect(highlightMatches(cy, "app")).toBe(1);
    expect(cy.$id("file:app.py").hasClass("match")).toBe(true);
    expect(cy.$id("file:lib/db.py").hasClass("search-dim")).toBe(true);
  });

  it("clears with an empty query", () => {
    const cy = headless();
    highlightMatches(cy, "app");

    expect(highlightMatches(cy, "  ")).toBe(0);
    expect(cy.$(".match, .search-dim")).toHaveLength(0);
  });

  it("returns 0 without fading when nothing matches", () => {
    const cy = headless();

    expect(highlightMatches(cy, "zzz")).toBe(0);
    expect(cy.$(".search-dim")).toHaveLength(0);
  });
});

describe("setHiddenTypes", () => {
  it("hides and shows node types", () => {
    const cy = headless();

    setHiddenTypes(cy, ["function"]);
    expect(cy.$id("s1").hasClass("hidden")).toBe(true);
    expect(cy.$id("file:app.py").hasClass("hidden")).toBe(false);

    setHiddenTypes(cy, []);
    expect(cy.$(".hidden")).toHaveLength(0);
  });
});

describe("layouts", () => {
  it("picks force-directed for small graphs and concentric for big ones", () => {
    expect(resolveLayout("auto", 50)).toBe("cose");
    expect(resolveLayout("auto", 3000)).toBe("clustered");
    expect(resolveLayout("grid", 3000)).toBe("grid");
  });

  it("runs every layout on a headless graph", () => {
    const cy = headless();

    for (const name of ["clustered", "cose", "breadthfirst", "concentric", "grid"] as const) {
      expect(() => cy.layout(layoutOptions(cy, name)).run()).not.toThrow();
    }
  });
});

describe("clusteredPositions", () => {
  // 30 files in a chain, each defining 0-59 symbols, plus unresolved calls.
  function bigGraph(): GraphResponse {
    const nodes: GraphResponse["nodes"] = [];
    const edges: GraphResponse["edges"] = [];
    for (let f = 0; f < 30; f++) {
      const file = `file:f${f}.py`;
      nodes.push({ id: file, type: "file", label: `f${f}.py`, path: `f${f}.py` });
      if (f > 0) edges.push({ id: `i${f}`, source: `file:f${f - 1}.py`, target: file, type: "imports" });
      for (let s = 0; s < (f * 2) % 60; s++) {
        nodes.push({ id: `s${f}-${s}`, type: "function", label: `fn${s}`, path: `f${f}.py` });
        edges.push({ id: `c${f}-${s}`, source: file, target: `s${f}-${s}`, type: "contains" });
      }
    }
    for (let x = 0; x < 50; x++) {
      nodes.push({ id: `x${x}`, type: "external", label: `ext${x}` });
      edges.push({ id: `k${x}`, source: `file:f${x % 30}.py`, target: `x${x}`, type: "calls" });
    }
    return { nodes, edges, files: 30, total_files: 30, truncated: false };
  }

  it("places every node, keeps symbols by their file, and separates files", async () => {
    const { clusteredPositions, clusterRadius } = await import("./clusterLayout");
    const graph = bigGraph();
    const cy = cytoscape({ headless: true, elements: toElements(graph) });

    const positions = clusteredPositions(cy);

    expect(Object.keys(positions)).toHaveLength(graph.nodes.length);
    for (const p of Object.values(positions)) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true);
    }

    const size = (f: number) => (f * 2) % 60;
    for (const edge of graph.edges.filter((e) => e.type === "contains")) {
      const file = positions[edge.source];
      const symbol = positions[edge.target];
      const f = Number(edge.source.match(/\d+/)![0]);
      expect(Math.hypot(file.x - symbol.x, file.y - symbol.y)).toBeLessThanOrEqual(
        clusterRadius(size(f)) + 0.001,
      );
    }

    // No two clusters overlap.
    for (let a = 0; a < 30; a++) {
      for (let b = a + 1; b < 30; b++) {
        const pa = positions[`file:f${a}.py`];
        const pb = positions[`file:f${b}.py`];
        expect(Math.hypot(pa.x - pb.x, pa.y - pb.y)).toBeGreaterThanOrEqual(
          clusterRadius(size(a)) + clusterRadius(size(b)) - 0.001,
        );
      }
    }
  });
});
