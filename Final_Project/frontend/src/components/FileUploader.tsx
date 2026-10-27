import { useRef, useState, type DragEvent } from "react";
import { api, ApiError, detectLanguage } from "../api/client";
import type { AnalyzeResponse } from "../api/types";
import FilePathLink from "./FilePathLink";

const MAX_FILE_BYTES = 1_000_000;

type ItemStatus = "queued" | "analyzing" | "done" | "error";

interface QueueItem {
  id: string;
  file: File;
  language: string | null;
  status: ItemStatus;
  result?: AnalyzeResponse;
  error?: string;
}

const STATUS_LABEL: Record<ItemStatus, string> = {
  queued: "Ready",
  analyzing: "Analyzing…",
  done: "Stored",
  error: "Failed",
};

function toItem(file: File): QueueItem {
  const language = detectLanguage(file.name);
  const tooLarge = file.size > MAX_FILE_BYTES;

  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    file,
    language,
    status: language && !tooLarge ? "queued" : "error",
    error: !language
      ? "Unsupported file type. Use .py, .js, .jsx, .ts, or a similar extension."
      : tooLarge
        ? "File is larger than 1 MB."
        : undefined,
  };
}

export default function FileUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<QueueItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [running, setRunning] = useState(false);

  function addFiles(fileList: FileList | null) {
    if (!fileList) return;

    setItems((current) => {
      const known = new Set(current.map((item) => item.id));
      const added = Array.from(fileList)
        .map(toItem)
        .filter((item) => !known.has(item.id));
      return [...current, ...added];
    });
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  }

  function update(id: string, patch: Partial<QueueItem>) {
    setItems((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }

  async function analyzeAll() {
    setRunning(true);

    // One at a time keeps the backend's Neo4j writes ordered.
    for (const item of items) {
      if (item.status !== "queued" || !item.language) continue;

      update(item.id, { status: "analyzing" });

      try {
        const sourceCode = await item.file.text();
        const result = await api.analyzeFile(
          item.file.name,
          sourceCode,
          item.language,
        );
        update(item.id, { status: "done", result });
      } catch (error) {
        update(item.id, {
          status: "error",
          error: error instanceof ApiError ? error.message : String(error),
        });
      }
    }

    setRunning(false);
  }

  function remove(id: string) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  const pending = items.filter((item) => item.status === "queued").length;

  return (
    <div>
      <div
        className={dragging ? "dropzone dropzone--active" : "dropzone"}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <p className="dropzone-title">Drop source files here</p>
        <p className="muted">Python, JavaScript, and TypeScript, up to 1 MB each.</p>
        <button
          type="button"
          className="button button--secondary"
          onClick={() => inputRef.current?.click()}
        >
          Choose files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".py,.pyi,.js,.jsx,.mjs,.cjs,.ts,.mts,.cts"
          onChange={(event) => {
            addFiles(event.target.files);
            event.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {items.length > 0 && (
        <>
          <ul className="file-list">
            {items.map((item) => (
              <li key={item.id} className="file-row">
                <div className="file-row-main">
                  <span className="path">{item.file.name}</span>
                  {item.language && <span className="tag">{item.language}</span>}
                  <span className={`state state--${item.status}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                  {item.status !== "analyzing" && (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => remove(item.id)}
                      aria-label={`Remove ${item.file.name}`}
                    >
                      Remove
                    </button>
                  )}
                </div>

                {item.error && <p className="error error--inline">{item.error}</p>}

                {item.result && (
                  <details className="file-result">
                    <summary>
                      {item.result.dependencies_found} dependencies,{" "}
                      {item.result.symbols_stored} symbols stored.{" "}
                      <FilePathLink path={item.file.name} />
                    </summary>
                    {item.result.dependencies.length === 0 ? (
                      <p className="muted">No dependencies found in this file.</p>
                    ) : (
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Target</th>
                            <th>Resolved to</th>
                          </tr>
                        </thead>
                        <tbody>
                          {item.result.dependencies.map((dependency, index) => (
                            <tr key={index}>
                              <td>{dependency.type}</td>
                              <td className="path">{dependency.target}</td>
                              <td className="path">
                                {dependency.resolved_target ?? "–"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </details>
                )}
              </li>
            ))}
          </ul>

          <div className="actions">
            <button
              type="button"
              className="button"
              disabled={running || pending === 0}
              onClick={analyzeAll}
            >
              {running
                ? "Analyzing…"
                : `Analyze ${pending} ${pending === 1 ? "file" : "files"}`}
            </button>
            <button
              type="button"
              className="button button--secondary"
              disabled={running}
              onClick={() => setItems([])}
            >
              Clear list
            </button>
          </div>
        </>
      )}
    </div>
  );
}
