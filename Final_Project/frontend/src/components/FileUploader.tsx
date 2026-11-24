import { useEffect, useRef, useState, type DragEvent } from "react";
import { api, ApiError, detectLanguage } from "../api/client";
import type { AnalyzeResponse } from "../api/types";
import FilePathLink from "./FilePathLink";

const MAX_FILE_BYTES = 1_000_000;

type ItemStatus = "queued" | "analyzing" | "done" | "error";

interface QueueItem {
  id: string;
  // Path stored in the graph; includes folders for files that came from a ZIP.
  path: string;
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

// Folders that hold dependencies or tooling, not the project's own code.
const SKIPPED_DIRS = /(^|\/)(node_modules|\.git|__pycache__|\.venv|venv|dist|build)\//;

function toItem(file: File, path = file.name): QueueItem {
  const language = detectLanguage(path);
  const tooLarge = file.size > MAX_FILE_BYTES;

  return {
    id: `${path}-${file.size}-${file.lastModified}`,
    path,
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

function isZip(file: File): boolean {
  return file.name.toLowerCase().endsWith(".zip");
}

// Unpacks the supported source files in a ZIP, keeping their folder paths.
export async function itemsFromZip(
  zipFile: File,
): Promise<{ items: QueueItem[]; skipped: number }> {
  // Loaded on demand so the main bundle stays small.
  const { default: JSZip } = await import("jszip");
  const zip = await JSZip.loadAsync(zipFile);
  const items: QueueItem[] = [];
  let skipped = 0;

  for (const entry of Object.values(zip.files)) {
    if (entry.dir) continue;
    if (!detectLanguage(entry.name) || SKIPPED_DIRS.test(entry.name)) {
      skipped += 1;
      continue;
    }

    const blob = await entry.async("blob");
    const file = new File([blob], entry.name.split("/").pop() ?? entry.name, {
      lastModified: entry.date.getTime(),
    });
    items.push(toItem(file, entry.name));
  }

  return { items, skipped };
}

export default function FileUploader() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<QueueItem[]>([]);
  const [dragging, setDragging] = useState(false);
  const [running, setRunning] = useState(false);
  const [unpacking, setUnpacking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [storedFiles, setStoredFiles] = useState<
    { path: string; language: string | null }[]
  >([]);
  const [removingStoredFile, setRemovingStoredFile] = useState<string | null>(null);
  const [storedFileError, setStoredFileError] = useState<string | null>(null);

  async function refreshStoredFiles() {
    try {
      setStoredFiles(await api.uploadedFiles());
      setStoredFileError(null);
    } catch (error) {
      setStoredFileError(error instanceof ApiError ? error.message : String(error));
    }
  }

  useEffect(() => {
    void refreshStoredFiles();
  }, []);

  async function deleteStoredFile(filePath: string) {
    if (!window.confirm(`Delete ${filePath} and its stored graph data? This cannot be undone.`)) {
      return;
    }
    setRemovingStoredFile(filePath);
    setStoredFileError(null);
    try {
      await api.deleteUploadedFile(filePath);
      await refreshStoredFiles();
    } catch (error) {
      setStoredFileError(error instanceof ApiError ? error.message : String(error));
    } finally {
      setRemovingStoredFile(null);
    }
  }

  async function addFiles(fileList: FileList | null) {
    if (!fileList) return;

    const files = Array.from(fileList);
    const added = files.filter((file) => !isZip(file)).map((file) => toItem(file));
    const messages: string[] = [];

    const zips = files.filter(isZip);
    if (zips.length > 0) {
      setUnpacking(true);
      for (const zipFile of zips) {
        try {
          const { items: zipItems, skipped } = await itemsFromZip(zipFile);
          added.push(...zipItems);
          messages.push(
            `${zipFile.name}: ${zipItems.length} source ${
              zipItems.length === 1 ? "file" : "files"
            } added` + (skipped ? `, ${skipped} other files skipped.` : "."),
          );
        } catch {
          messages.push(`${zipFile.name} could not be read as a ZIP archive.`);
        }
      }
      setUnpacking(false);
    }

    setNotice(messages.length ? messages.join(" ") : null);
    setItems((current) => {
      const known = new Set(current.map((item) => item.id));
      return [...current, ...added.filter((item) => !known.has(item.id))];
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
          item.path,
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

    await refreshStoredFiles();
    setRunning(false);
  }

  function remove(id: string) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  const pending = items.filter((item) => item.status === "queued").length;

  return (
    <div>
      <section className="repository-manager" aria-label="Manage uploaded files">
        <div className="repository-manager-heading">
          <div>
            <h2>Manage uploaded files</h2>
            <p className="muted">Remove files that are already stored in the graph.</p>
          </div>
        </div>
        {storedFileError && <p className="error error--inline">{storedFileError}</p>}
        {storedFiles.length === 0 ? (
          <p className="muted">No uploaded files are currently stored.</p>
        ) : (
          <ul className="repository-list">
            {storedFiles.map((item) => (
              <li className="repository-row" key={item.path}>
                <div className="repository-row-info">
                  <strong className="path">{item.path}</strong>
                  <span className="muted">{item.language ?? "Unknown language"}</span>
                </div>
                <button
                  type="button"
                  className="button button--danger"
                  disabled={removingStoredFile !== null}
                  onClick={() => deleteStoredFile(item.path)}
                >
                  {removingStoredFile === item.path ? "Removing…" : "Remove"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

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
        <p className="muted">
          Python, JavaScript, and TypeScript, up to 1 MB each, or a ZIP of a project.
        </p>
        <button
          type="button"
          className="button button--secondary"
          disabled={unpacking}
          onClick={() => inputRef.current?.click()}
        >
          {unpacking ? "Unpacking…" : "Choose files"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          accept=".py,.pyi,.js,.jsx,.mjs,.cjs,.ts,.mts,.cts,.zip"
          onChange={(event) => {
            addFiles(event.target.files);
            event.target.value = ""; // allow re-selecting the same file
          }}
        />
      </div>

      {notice && <p className="muted">{notice}</p>}

      {items.length > 0 && (
        <>
          <ul className="file-list">
            {items.map((item) => (
              <li key={item.id} className="file-row">
                <div className="file-row-main">
                  <span className="path">{item.path}</span>
                  {item.language && <span className="tag">{item.language}</span>}
                  <span className={`state state--${item.status}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                  {item.status !== "analyzing" && (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => remove(item.id)}
                      aria-label={`Remove ${item.path}`}
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
                      <FilePathLink path={item.path} />
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
