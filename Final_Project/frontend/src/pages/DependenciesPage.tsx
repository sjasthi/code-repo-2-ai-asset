import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { DependencySearchResponse, FileSearchResult } from "../api/types";
import ErrorMessage from "../components/ErrorMessage";
import FilePathLink from "../components/FilePathLink";

export default function DependenciesPage() {
  const [query, setQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [files, setFiles] = useState<FileSearchResult[]>([]);
  const [total, setTotal] = useState(0);

  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [dependencyLoading, setDependencyLoading] = useState(false);
  const [dependencyError, setDependencyError] = useState<string | null>(null);
  const [dependencies, setDependencies] = useState<DependencySearchResponse | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;

    setSearchLoading(true);
    setSearchError(null);
    setSearched(false);
    setFiles([]);
    setTotal(0);
    setSelectedFile(null);
    setDependencies(null);
    setDependencyError(null);

    try {
      const response = await api.searchFiles(q);
      setFiles(response.results);
      setTotal(response.total);
      setSearched(true);
    } catch (err) {
      setSearchError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setSearchLoading(false);
    }
  }

  async function showDependencies(path: string) {
    setSelectedFile(path);
    setDependencies(null);
    setDependencyError(null);
    setDependencyLoading(true);

    try {
      const result = await api.searchDependencies({ query: path, target: "file" });
      setDependencies(result);
    } catch (err) {
      setDependencyError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setDependencyLoading(false);
    }
  }

  return (
    <>
      <h1>Dependencies</h1>
      <p className="lead">
        Search for a file by its name or part of its path, then see what it imports
        and which files depend on it.
      </p>

      <form className="form" onSubmit={onSubmit}>
        <div className="search-row">
          <input
            type="search"
            aria-label="Search files"
            placeholder="Search files, e.g. main.py or backend/app"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" className="button" disabled={searchLoading || !query.trim()}>
            {searchLoading ? "Searching…" : "Search files"}
          </button>
        </div>
      </form>

      {searchError && <ErrorMessage message={searchError} />}

      {searched && (
        <section aria-live="polite">
          <p className="muted">
            {total === 0
              ? `No files found matching “${query.trim()}”. Check the spelling or import a repository first.`
              : `Found ${total} file${total === 1 ? "" : "s"}. Select a file to inspect its dependencies.`}
          </p>

          {files.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>File</th><th>Language</th><th>Match</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.path}>
                      <td><FilePathLink path={file.path} /></td>
                      <td>{file.language ?? "–"}</td>
                      <td>{file.match}</td>
                      <td>
                        <button
                          type="button"
                          className="button button--secondary"
                          disabled={dependencyLoading && selectedFile === file.path}
                          onClick={() => showDependencies(file.path)}
                        >
                          {dependencyLoading && selectedFile === file.path
                            ? "Loading…"
                            : "Show dependencies"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {selectedFile && (
        <section className="dependency-results" aria-live="polite">
          <div className="section-heading">
            <h2>Dependencies: {selectedFile}</h2>
            <button
              type="button"
              className="button button--secondary"
              onClick={() => {
                setSelectedFile(null);
                setDependencies(null);
                setDependencyError(null);
              }}
            >
              Close
            </button>
          </div>

          {dependencyLoading && <p className="muted">Loading dependencies…</p>}
          {dependencyError && <ErrorMessage message={dependencyError} />}

          {dependencies && (
            <>
              <div className="dependency-columns">
                <DependencyList
                  title={`Imports (${dependencies.imports.length})`}
                  paths={dependencies.imports}
                  empty="This file does not import any stored project files."
                />
                <DependencyList
                  title={`Imported by (${dependencies.imported_by.length})`}
                  paths={dependencies.imported_by}
                  empty="No stored project files import this file."
                />
                <section>
                  <h3>Functions called ({dependencies.calls.length})</h3>
                  {dependencies.calls.length === 0 ? (
                    <p className="muted">No stored function calls from this file.</p>
                  ) : (
                    <ul>
                      {dependencies.calls.map((call, index) => (
                        <li key={`${call.name}:${call.line}:${index}`}>
                          {call.name}{call.line != null ? ` (line ${call.line})` : ""}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
              <p>
                <Link to={`/graph?file=${encodeURIComponent(dependencies.file_path)}&depth=2&symbols=1&calls=1`}>
                  Open this file in the dependency graph
                </Link>
              </p>
            </>
          )}
        </section>
      )}
    </>
  );
}

function DependencyList({
  title,
  paths,
  empty,
}: {
  title: string;
  paths: string[];
  empty: string;
}) {
  return (
    <section>
      <h3>{title}</h3>
      {paths.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul className="path-list">
          {paths.map((path) => <li key={path}><FilePathLink path={path} /></li>)}
        </ul>
      )}
    </section>
  );
}
