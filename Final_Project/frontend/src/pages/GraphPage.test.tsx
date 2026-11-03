import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api/client";
import type { GraphResponse } from "../api/types";
import GraphPage from "./GraphPage";

// The canvas needs a real browser to draw; stand in a simple version that
// lists its nodes as buttons so tests can "click" them.
vi.mock("../components/GraphCanvas", () => ({
  default: (props: {
    elements: { group: string; data: { id: string; label: string } }[];
    search: string;
    selectedId: string | null;
    onSelect: (id: string | null) => void;
  }) => (
    <div data-testid="canvas" data-selected={props.selectedId ?? ""} data-search={props.search}>
      {props.elements
        .filter((element) => element.group === "nodes")
        .map((element) => (
          <button key={element.data.id} type="button" onClick={() => props.onSelect(element.data.id)}>
            node {element.data.label}
          </button>
        ))}
    </div>
  ),
}));

const GRAPH: GraphResponse = {
  nodes: [
    { id: "file:app.py", type: "file", label: "app.py", path: "app.py", language: "python" },
    { id: "file:lib/helpers.py", type: "file", label: "helpers.py", path: "lib/helpers.py", language: "python" },
  ],
  edges: [{ id: "e1", source: "file:app.py", target: "file:lib/helpers.py", type: "imports" }],
  files: 2,
  total_files: 2,
  truncated: false,
};

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

function renderAt(url: string) {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/graph" element={<GraphPage />} />
        <Route path="*" element={null} />
      </Routes>
      <Location />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.spyOn(api, "graphProjects").mockResolvedValue([
    { id: "github.com/psf/requests/", label: "github.com/psf/requests", files: 37 },
    { id: "uploads", label: "Uploaded files", files: 2 },
  ]);
});

describe("GraphPage", () => {
  it("loads the graph and shows a summary", async () => {
    const graph = vi.spyOn(api, "graph").mockResolvedValue(GRAPH);

    renderAt("/graph");

    expect(await screen.findByText("node app.py")).toBeInTheDocument();
    expect(screen.getByText(/2 files, 2 nodes, 1 links/)).toBeInTheDocument();
    expect(graph).toHaveBeenCalledWith({
      project: "",
      file: "",
      depth: 1,
      includeSymbols: false,
      includeCalls: false,
      limit: 1000,
    });
    expect(await screen.findByRole("option", { name: "Uploaded files (2 files)" })).toBeInTheDocument();
  });

  it("refetches with symbols when the checkbox is ticked and keeps it in the URL", async () => {
    const graph = vi.spyOn(api, "graph").mockResolvedValue(GRAPH);
    renderAt("/graph?project=uploads");
    await screen.findByText("node app.py");

    await userEvent.click(screen.getByRole("checkbox", { name: /Classes, functions/ }));

    expect(graph).toHaveBeenLastCalledWith(
      expect.objectContaining({ project: "uploads", includeSymbols: true }),
    );
    expect(screen.getByTestId("location")).toHaveTextContent("/graph?project=uploads&symbols=1");
  });

  it("shows what a clicked file imports and what imports it", async () => {
    vi.spyOn(api, "graph").mockResolvedValue(GRAPH);
    renderAt("/graph");

    await userEvent.click(await screen.findByText("node helpers.py"));

    const panel = screen.getByRole("complementary", { name: "Selected node" });
    expect(within(panel).getByRole("heading", { name: "helpers.py" })).toBeInTheDocument();
    expect(within(panel).getByText("Imports (0)")).toBeInTheDocument();
    expect(within(panel).getByText("Imported by (1)")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Dependency list" })).toHaveAttribute(
      "href",
      "/dependencies?file=lib%2Fhelpers.py",
    );

    // Related nodes are buttons, so the graph can be explored by keyboard.
    await userEvent.click(within(panel).getByRole("button", { name: "app.py" }));
    expect(screen.getByTestId("canvas")).toHaveAttribute("data-selected", "file:app.py");
  });

  it("centers on a file from the details panel", async () => {
    const graph = vi.spyOn(api, "graph").mockResolvedValue(GRAPH);
    renderAt("/graph");

    await userEvent.click(await screen.findByText("node app.py"));
    await userEvent.click(screen.getByRole("button", { name: "Center graph here" }));

    expect(graph).toHaveBeenLastCalledWith(expect.objectContaining({ file: "app.py" }));
    expect(await screen.findByTestId("canvas")).toHaveAttribute("data-selected", "file:app.py");
  });

  it("passes the highlight query from the URL to the graph", async () => {
    vi.spyOn(api, "graph").mockResolvedValue(GRAPH);
    renderAt("/graph?file=app.py&symbols=1&q=helper");

    expect(await screen.findByTestId("canvas")).toHaveAttribute("data-search", "helper");
    expect(screen.getByRole("searchbox", { name: "Highlight nodes" })).toHaveValue("helper");
  });

  it("explains a truncated graph", async () => {
    vi.spyOn(api, "graph").mockResolvedValue({ ...GRAPH, truncated: true, total_files: 4200 });
    renderAt("/graph");

    expect(await screen.findByText(/Showing the first 2 of 4200 files/)).toBeInTheDocument();
  });

  it("says when a centered file isn't stored", async () => {
    vi.spyOn(api, "graph").mockResolvedValue({ ...GRAPH, nodes: [], edges: [], files: 0, total_files: 0 });
    renderAt("/graph?file=missing.py");

    expect(await screen.findByText(/No stored file at “missing.py”/)).toBeInTheDocument();
    expect(screen.queryByTestId("canvas")).not.toBeInTheDocument();
  });

  it("shows API errors", async () => {
    vi.spyOn(api, "graph").mockRejectedValue(new ApiError("Neo4j is down", 503));
    renderAt("/graph");

    expect(await screen.findByRole("alert")).toHaveTextContent("Neo4j is down");
  });
});
