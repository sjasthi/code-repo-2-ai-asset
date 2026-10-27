import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import ErrorMessage from "../components/ErrorMessage";
import FilePathLink from "../components/FilePathLink";

interface Neighbours {
  imports: string[];
  importedBy: string[];
}

export default function DependenciesPage() {
  const [params, setParams] = useSearchParams();
  const file = params.get("file") ?? "";

  const [input, setInput] = useState(file);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<Neighbours | null>(null);

  // The URL is the source of truth, so links from other pages and the
  // back button both work.
  useEffect(() => {
    setInput(file);

    if (!file) {
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([api.fileImports(file), api.fileImportedBy(file)])
      .then(([imports, importedBy]) => {
        if (cancelled) return;
        setData({
          imports: imports.map((row) => row.imported_file),
          importedBy: importedBy.map((row) => row.importing_file),
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setData(null);
        setError(err instanceof ApiError ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [file]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const path = input.trim();
    if (path) setParams({ file: path });
  }

  return (
    <>
      <h1>Dependencies</h1>
      <p className="lead">See what a file imports and which files import it.</p>

      <form className="form" onSubmit={onSubmit}>
        <div className="search-row">
          <input
            type="text"
            aria-label="File path"
            placeholder="example.py"
            value={input}
            onChange={(event) => setInput(event.target.value)}
          />
          <button type="submit" className="button" disabled={loading || !input.trim()}>
            {loading ? "Loading…" : "Show dependencies"}
          </button>
        </div>
      </form>

      {!file && (
        <p className="muted">
          Enter a file path exactly as stored, or <Link to="/search">search for a file</Link>.
        </p>
      )}

      {error && <ErrorMessage message={error} />}

      {data && (
        <div className="columns">
          <section>
            <h2>Imports ({data.imports.length})</h2>
            {data.imports.length === 0 ? (
              <p className="muted">This file doesn’t import any stored files.</p>
            ) : (
              <ul className="path-list">
                {data.imports.map((path) => (
                  <li key={path}>
                    <FilePathLink path={path} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2>Imported by ({data.importedBy.length})</h2>
            {data.importedBy.length === 0 ? (
              <p className="muted">No stored file imports this one.</p>
            ) : (
              <ul className="path-list">
                {data.importedBy.map((path) => (
                  <li key={path}>
                    <FilePathLink path={path} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {data.imports.length === 0 && data.importedBy.length === 0 && (
            <p className="muted columns-note">
              If you expected results, check that the path matches how the file was
              stored, and that it was analyzed on the Upload page.
            </p>
          )}
        </div>
      )}
    </>
  );
}
