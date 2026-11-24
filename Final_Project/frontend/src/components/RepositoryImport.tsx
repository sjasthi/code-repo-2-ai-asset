
import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { ImportProgress, RepositoryImportResponse } from "../api/types";
import ErrorMessage from "./ErrorMessage";

// "https://github.com/Owner/Repo(.git)(/tree/x)" -> "owner/repo", or null.
function repositoryKey(url: string): string | null {
  try {
    const parts = new URL(url).pathname.split("/").filter(Boolean);
    if (parts.length < 2) return null;
    return `${parts[0]}/${parts[1].replace(/\.git$/, "")}`.toLowerCase();
  } catch {
    return null;
  }
}

// True when this repository is already in the graph. A failed lookup is
// treated as "not imported" so it never blocks an import.
async function isAlreadyImported(url: string): Promise<boolean> {
  const key = repositoryKey(url);
  if (!key) return false;
  try {
    const projects = await api.graphProjects();
    return projects.some(
      (project) =>
        project.id.toLowerCase().replace(/\/$/, "") === `github.com/${key}`,
    );
  } catch {
    return false;
  }
}

function formatDuration(seconds: number): string {
  const total = Math.max(1, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const minutes = Math.floor(total / 60);
  return `${minutes}m ${total % 60}s`;
}

// Remaining time is extrapolated from the average pace so far. It is hidden
// until there is enough data for it to be meaningful.
function estimateRemaining(progress: number, elapsedSeconds: number) {
  if (progress < 0.05 || elapsedSeconds < 3 || progress >= 1) return null;
  return (elapsedSeconds / progress) * (1 - progress);
}

export default function RepositoryImport() {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] =
    useState<RepositoryImportResponse | null>(null);
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef(0);

  // Tick once a second so elapsed time and the estimate stay current even
  // when the backend is busy on a single long step.
  useEffect(() => {
    if (!loading) return;
    const timer = window.setInterval(() => {
      setElapsed((Date.now() - startedAt.current) / 1000);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [loading]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();

    if (
      (await isAlreadyImported(url.trim())) &&
      !window.confirm(
        "This repository is already in the database. Importing it again " +
          "will replace its existing graph data. Are you sure you want to re-import it?",
      )
    ) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(null);
    setElapsed(0);
    startedAt.current = Date.now();

    try {
      const response = await api.importRepositoryStream(
        url.trim(),
        branch.trim(),
        (update) => {
          setProgress(update);
          setElapsed((Date.now() - startedAt.current) / 1000);
        },
      );

      // Only show completion after the backend confirms success.
      setResult(response);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : String(err),
      );
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
          <button
            type="submit"
            className="button"
            disabled={loading || !url.trim()}
          >
            {loading ? "Importing…" : "Import repository"}
          </button>
        </div>
      </form>

      {loading && (
        <div className="import-progress">
          <div
            className="progress-bar"
            role="progressbar"
            aria-label="Import progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round((progress?.progress ?? 0) * 100)}
          >
            <div
              className="progress-bar__fill"
              style={{ width: `${(progress?.progress ?? 0) * 100}%` }}
            />
          </div>

          <p className="muted" role="status" aria-live="off">
            <strong>{Math.round((progress?.progress ?? 0) * 100)}%</strong>
            {" · "}
            {progress?.message ?? "Starting import…"}
          </p>

          <p className="muted">
            Elapsed {formatDuration(elapsed)}
            {(() => {
              const remaining = estimateRemaining(
                progress?.progress ?? 0,
                elapsed,
              );
              return remaining === null
                ? " · estimating time remaining…"
                : ` · about ${formatDuration(remaining)} remaining`;
            })()}
          </p>
        </div>
      )}

      {error && <ErrorMessage message={error} />}

      {result && (
        <section
          className="summary"
          aria-label="Import result"
          role="status"
          aria-live="polite"
        >
          {/* NEW: Explicit GitHub import completion message */}
          <h3>
            <span aria-hidden="true">✓ </span>
            GitHub import completed successfully!
          </h3>

          <p>
            Successfully imported{" "}
            <strong className="path">{result.repository}</strong>{" "}
            on branch <strong>{result.branch}</strong>.
          </p>

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
            Your repository data is stored under{" "}
            <span className="path">
              {result.graph_path_prefix}
            </span>
            . You can now search for its files and explore the graph.
          </p>
        </section>
      )}
    </div>
  );
}
