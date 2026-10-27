import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { RepositoryImportResponse } from "../api/types";
import ErrorMessage from "./ErrorMessage";

export default function RepositoryImport() {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RepositoryImportResponse | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      setResult(await api.importRepository(url.trim(), branch.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form className="form" onSubmit={onSubmit}>
        <label className="field">
          <span className="field-label">Repository URL</span>
          <input
            type="url"
            required
            placeholder="https://github.com/owner/repository"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
        </label>

        <label className="field field--narrow">
          <span className="field-label">Branch (optional)</span>
          <input
            type="text"
            placeholder="default branch"
            value={branch}
            onChange={(event) => setBranch(event.target.value)}
          />
        </label>

        <div className="actions">
          <button type="submit" className="button" disabled={loading || !url.trim()}>
            {loading ? "Importing…" : "Import repository"}
          </button>
        </div>
      </form>

      {loading && (
        <p className="muted">Cloning and analyzing files. Large repositories can take a while.</p>
      )}
      {error && <ErrorMessage message={error} />}

      {result && (
        <section className="summary" aria-label="Import result">
          <h3>
            Imported <span className="path">{result.repository}</span> ({result.branch})
          </h3>
          <dl className="stats">
            <div>
              <dt>Files analyzed</dt>
              <dd>{result.files_analyzed}</dd>
            </div>
            <div>
              <dt>Symbols stored</dt>
              <dd>{result.symbols_stored}</dd>
            </div>
            <div>
              <dt>Relationships stored</dt>
              <dd>{result.relationships_stored}</dd>
            </div>
            <div>
              <dt>Files with syntax errors</dt>
              <dd>{result.files_with_syntax_errors}</dd>
            </div>
          </dl>
          <p className="muted">
            Files are stored under <span className="path">{result.graph_path_prefix}</span>.
            Search for that prefix to browse them.
          </p>
        </section>
      )}
    </div>
  );
}
