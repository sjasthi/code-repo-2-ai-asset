import { useDeferredValue, useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { GraphNode, GraphNodeType, GraphProject, GraphResponse } from "../api/types";
import ErrorMessage from "../components/ErrorMessage";
import GraphCanvas from "../components/GraphCanvas";
import {
  describeNode,
  LARGE_GRAPH_NODES,
  LAYOUTS,
  NODE_LOOK,
  NODE_TYPES,
  toElements,
  type LayoutName,
} from "../graph/model";

// Keep the initial overview lightweight; expand details around a file on demand.
const FILE_LIMIT = 500;

const TYPE_NAME: Record<GraphNodeType, string> = {
  file: "File",
  class: "Class",
  function: "Function",
  method: "Method",
  variable: "Variable",
  external: "Unresolved call",
};

export default function GraphPage() {
  const [params, setParams] = useSearchParams();
  const project = params.get("project") ?? "";
  const file = params.get("file") ?? "";
  const depth = Number(params.get("depth") ?? 1) || 1;
  const includeSymbols = params.get("symbols") === "1";
  const includeCalls = params.get("calls") === "1";
  // Import lines are off unless the URL opts in with ?imports=1.
  const hideImports = params.get("imports") !== "1";
  const focusName = params.get("focus") ?? "";
  const focusType = params.get("focusType") ?? "";
  const focusLine = params.get("focusLine");
  const graphQuery = params.get("q");
  const hasGraphQuery = params.has("q");

  const [projects, setProjects] = useState<GraphProject[]>([]);
  const [removingProject, setRemovingProject] = useState<string | null>(null);
  const [projectActionError, setProjectActionError] = useState<string | null>(null);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fileInput, setFileInput] = useState(file);
  const [layout, setLayout] = useState<LayoutName>("auto");
  const [hiddenTypes, setHiddenTypes] = useState<GraphNodeType[]>([]);
  const [search, setSearch] = useState(params.get("q") ?? "");
  const [matchCount, setMatchCount] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Typing stays responsive on big graphs; the highlight catches up.
  const deferredSearch = useDeferredValue(search);

  function updateParams(patch: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(patch)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next);
  }

  async function refreshProjects() {
    const updatedProjects = await api.graphProjects();
    setProjects(updatedProjects);
  }

  useEffect(() => {
    let cancelled = false;
    api.graphProjects()
      .then((items) => {
        if (!cancelled) setProjects(items);
      })
      .catch(() => {
        if (!cancelled) setProjects([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function removeRepository(repositoryProject: GraphProject) {
    const match = /^github\.com\/([^/]+)\/([^/]+)\/$/.exec(repositoryProject.id);
    if (!match) {
      setProjectActionError("This item is not a GitHub repository.");
      return;
    }

    const [, owner, repository] = match;
    const confirmed = window.confirm(
      `Delete ${owner}/${repository} and all of its indexed graph data? This cannot be undone.`,
    );
    if (!confirmed) return;

    setRemovingProject(repositoryProject.id);
    setProjectActionError(null);
    try {
      await api.deleteRepository(owner, repository);
      await refreshProjects();

      if (
        project === repositoryProject.id ||
        file.startsWith(repositoryProject.id)
      ) {
        updateParams({
          project: null,
          file: null,
          focus: null,
          focusType: null,
          focusLine: null,
        });
      }
    } catch (err) {
      setProjectActionError(
        err instanceof ApiError ? err.message : String(err),
      );
    } finally {
      setRemovingProject(null);
    }
  }

  useEffect(() => {
    setFileInput(file);
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .graph({ project, file, depth, includeSymbols, includeCalls, limit: FILE_LIMIT })
      .then((response) => {
        if (cancelled) return;
        setGraph(response);
        if (focusName) {
          const focusedNode = response.nodes.find((node) =>
            node.label === focusName &&
            node.path === file &&
            (!focusType || node.type === focusType) &&
            (focusLine == null || String(node.line ?? "") === focusLine)
          ) ?? response.nodes.find((node) =>
            node.label === focusName && node.path === file && (!focusType || node.type === focusType)
          );
          setSelectedId(focusedNode?.id ?? (file ? `file:${file}` : null));
          setSearch(focusName);
        } else {
          setSelectedId(file ? `file:${file}` : null);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setGraph(null);
        setError(err instanceof ApiError ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [project, file, depth, includeSymbols, includeCalls, focusName, focusType, focusLine]);

  useEffect(() => {
    if (hasGraphQuery) setSearch(graphQuery ?? "");
  }, [graphQuery, hasGraphQuery]);

  // Import lines are hidden only in the drawing; the details panel still
  // lists a file's imports from the full graph.
  const elements = useMemo(() => {
    if (!graph) return [];
    return toElements(
      hideImports
        ? { ...graph, edges: graph.edges.filter((edge) => edge.type !== "imports") }
        : graph,
    );
  }, [graph, hideImports]);
  const details = useMemo(
    () => (graph && selectedId ? describeNode(graph, selectedId) : null),
    [graph, selectedId],
  );
  const presentTypes = useMemo(
    () => new Set(graph?.nodes.map((node) => node.type) ?? []),
    [graph],
  );

  function onCenter(event: FormEvent) {
    event.preventDefault();
    updateParams({ file: fileInput.trim() || null });
  }

  function toggleType(type: GraphNodeType) {
    setHiddenTypes((current) =>
      current.includes(type) ? current.filter((t) => t !== type) : [...current, type],
    );
  }

  const nodeCount = graph?.nodes.length ?? 0;

  return (
    <>
      <h1>Dependency graph</h1>
      <p className="lead">
        Explore how files import each other. Click a node to highlight what it
        depends on and what depends on it.
      </p>

      <div className="graph-controls">
        <label className="field">
          <span className="field-label">Show</span>
          <select
            value={project}
            disabled={Boolean(file)}
            onChange={(event) => updateParams({ project: event.target.value || null })}
          >
            <option value="">All files</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label} ({p.files} {p.files === 1 ? "file" : "files"})
              </option>
            ))}
          </select>
        </label>

        <form className="field graph-center" onSubmit={onCenter}>
          <span className="field-label">Center on file</span>
          <div className="search-row">
            <input
              type="text"
              aria-label="Center on file"
              placeholder="dependency_app.py"
              value={fileInput}
              onChange={(event) => setFileInput(event.target.value)}
            />
            <select
              aria-label="Import hops"
              value={depth}
              onChange={(event) => updateParams({ depth: event.target.value })}
            >
              <option value={1}>1 hop</option>
              <option value={2}>2 hops</option>
              <option value={3}>3 hops</option>
            </select>
            <button type="submit" className="button button--secondary" disabled={!fileInput.trim()}>
              Center
            </button>
            {file && (
              <button
                type="button"
                className="button button--secondary"
                onClick={() => updateParams({ file: null })}
              >
                Show all
              </button>
            )}
          </div>
        </form>

        <label className="field">
          <span className="field-label">Layout</span>
          <select value={layout} onChange={(event) => setLayout(event.target.value as LayoutName)}>
            {LAYOUTS.map((option) => (
              <option key={option.name} value={option.name}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-label">Highlight</span>
          <input
            type="search"
            aria-label="Highlight nodes"
            placeholder="Name or path"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>

      {projects.some((item) => item.id.startsWith("github.com/")) && (
        <details className="repository-manager">
          <summary className="repository-manager-heading">
            <span>
              <h2>Manage imported repositories</h2>
              <p className="muted">Remove old imports and their indexed graph data.</p>
            </span>
          </summary>
          {projectActionError && <ErrorMessage message={projectActionError} />}
          <ul className="repository-list">
            {projects
              .filter((item) => item.id.startsWith("github.com/"))
              .map((item) => (
                <li className="repository-row" key={item.id}>
                  <div className="repository-row-info">
                    <strong>{item.label}</strong>
                    <span className="muted">
                      {item.files} {item.files === 1 ? "file" : "files"}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="button button--danger"
                    disabled={removingProject !== null}
                    onClick={() => removeRepository(item)}
                  >
                    {removingProject === item.id ? "Removing…" : "Remove"}
                  </button>
                </li>
              ))}
          </ul>
        </details>
      )}

      <fieldset className="filters graph-filters">
        <legend>Include</legend>
        <label className="check">
          <input
            type="checkbox"
            checked={includeSymbols}
            onChange={(event) => updateParams({ symbols: event.target.checked ? "1" : null })}
          />
          Classes, functions &amp; variables
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={includeCalls}
            onChange={(event) => updateParams({ calls: event.target.checked ? "1" : null })}
          />
          Function calls
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={!hideImports}
            onChange={(event) => updateParams({ imports: event.target.checked ? "1" : null })}
          />
          Import lines
        </label>
      </fieldset>

      {presentTypes.size > 1 && (
        <fieldset className="filters graph-filters">
          <legend>Show types</legend>
          {NODE_TYPES.filter(({ type }) => presentTypes.has(type)).map(({ type, label }) => (
            <label key={type} className="check">
              <input
                type="checkbox"
                checked={!hiddenTypes.includes(type)}
                onChange={() => toggleType(type)}
              />
              <span
                className={`swatch swatch--${NODE_LOOK[type].shape}`}
                style={{ ["--swatch" as string]: NODE_LOOK[type].color }}
                aria-hidden="true"
              />
              {label}
            </label>
          ))}
        </fieldset>
      )}

      {error && <ErrorMessage message={error} />}

      {graph && (
        <p className="muted graph-status" aria-live="polite">
          {loading ? "Loading… " : ""}
          {graph.files} {graph.files === 1 ? "file" : "files"}, {nodeCount} nodes,{" "}
          {graph.edges.length} links.
          {graph.truncated &&
            ` Showing the first ${graph.files} of ${graph.total_files ?? "more"} files; select a project or center on a file to narrow the view.`}
          {graph.nodes_truncated && " Symbol/call node limit reached; center on a file to inspect a smaller area."}
          {graph.edges_truncated && " Relationship limit reached; some links are hidden. Center on a file to inspect a smaller area."}
          {nodeCount > LARGE_GRAPH_NODES && " Large graph: labels appear as you zoom in."}
          {deferredSearch.trim() &&
            ` ${matchCount} ${matchCount === 1 ? "match" : "matches"} for “${deferredSearch.trim()}”.`}
        </p>
      )}
      {!graph && loading && <p className="muted">Loading graph…</p>}

      {graph && nodeCount === 0 && (
        <p className="muted">
          {file
            ? `No stored file at “${file}”. Check the path, or `
            : "Nothing to show yet. "}
          <Link to="/upload">Add code on the Upload page</Link>.
        </p>
      )}

      {graph && nodeCount > 0 && (
        <div className="graph-layout">
          <GraphCanvas
            elements={elements}
            layout={layout}
            hiddenTypes={hiddenTypes}
            search={deferredSearch}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onMatchCount={setMatchCount}
          />

          <aside className="graph-panel" aria-label="Selected node">
            {details ? (
              <NodePanel
                details={details}
                onSelect={setSelectedId}
                onCenter={(path) => updateParams({ file: path })}
                onExpandDetails={(path) => updateParams({ file: path, symbols: "1", calls: "1" })}
              />
            ) : (
              <>
                <h2>Details</h2>
                <p className="muted">
                  Click a node to see what it imports and what imports it.
                  Scroll to zoom, drag to pan.
                </p>
                <ul className="graph-legend">
                  <li><span className="legend-line legend-line--imports" /> imports</li>
                  <li><span className="legend-line legend-line--contains" /> defines (contains)</li>
                  <li><span className="legend-line legend-line--calls" /> calls</li>
                </ul>
              </>
            )}
          </aside>
        </div>
      )}
    </>
  );
}

function NodePanel({
  details,
  onSelect,
  onCenter,
  onExpandDetails,
}: {
  details: NonNullable<ReturnType<typeof describeNode>>;
  onSelect: (id: string) => void;
  onCenter: (path: string) => void;
  onExpandDetails: (path: string) => void;
}) {
  const { node } = details;
  const isFile = node.type === "file";
  const filePath = isFile ? node.path : details.definedIn?.path ?? node.path;

  return (
    <>
      <h2 className="graph-panel-title">{node.label}</h2>
      <p className="graph-panel-meta">
        <span className="tag">{TYPE_NAME[node.type]}</span>
        {node.language && <span className="tag">{node.language}</span>}
        {node.line != null && <span className="muted">line {node.line}</span>}
      </p>
      {node.path && <p className="path graph-panel-path">{node.path}</p>}

      <div className="actions graph-panel-actions">
        {filePath && (
          <button type="button" className="button button--secondary" onClick={() => onCenter(filePath)}>
            Center graph here
          </button>
        )}
        {filePath && (
          <button type="button" className="button button--primary" onClick={() => onExpandDetails(filePath)}>
            Expand symbols &amp; calls
          </button>
        )}
        {isFile && node.path && (
          <Link
            className="button button--secondary"
            to={`/dependencies?file=${encodeURIComponent(node.path)}`}
          >
            Dependency list
          </Link>
        )}
      </div>

      {details.definedIn && <Related title="Defined in" nodes={[details.definedIn]} onSelect={onSelect} />}
      <Related title="Imports" tone="outgoing" nodes={details.imports} showEmpty={isFile} onSelect={onSelect} />
      <Related title="Imported by" tone="incoming" nodes={details.importedBy} showEmpty={isFile} onSelect={onSelect} />
      <Related title="Defines" nodes={details.contains} onSelect={onSelect} />
      <Related title="Calls" nodes={details.calls} onSelect={onSelect} />
    </>
  );
}

function Related({
  title,
  nodes,
  tone,
  showEmpty = false,
  onSelect,
}: {
  title: string;
  nodes: GraphNode[];
  tone?: "outgoing" | "incoming";
  showEmpty?: boolean;
  onSelect: (id: string) => void;
}) {
  if (nodes.length === 0 && !showEmpty) return null;

  return (
    <section className="graph-related">
      <h3 className={tone ? `graph-related-title graph-related-title--${tone}` : "graph-related-title"}>
        {title} ({nodes.length})
      </h3>
      {nodes.length === 0 ? (
        <p className="muted">None in this view.</p>
      ) : (
        <ul>
          {nodes.map((other) => (
            <li key={other.id}>
              <button
                type="button"
                className="graph-node-link"
                title={other.path ?? other.label}
                onClick={() => onSelect(other.id)}
              >
                {other.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
