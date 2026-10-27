import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type {
  FileSearchResult,
  SymbolSearchResult,
  SymbolType,
} from "../api/types";
import ErrorMessage from "../components/ErrorMessage";
import FilePathLink from "../components/FilePathLink";

type Mode = "symbols" | "files";

const SYMBOL_TYPES: SymbolType[] = ["class", "function", "method", "variable"];

export default function SearchPage() {
  const [mode, setMode] = useState<Mode>("symbols");
  const [query, setQuery] = useState("");
  const [types, setTypes] = useState<SymbolType[]>([]);
  const [fuzzy, setFuzzy] = useState(true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState<{ query: string; mode: Mode } | null>(null);
  const [total, setTotal] = useState(0);
  const [symbols, setSymbols] = useState<SymbolSearchResult[]>([]);
  const [files, setFiles] = useState<FileSearchResult[]>([]);

  function toggleType(type: SymbolType) {
    setTypes((current) =>
      current.includes(type)
        ? current.filter((item) => item !== type)
        : [...current, type],
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;

    setLoading(true);
    setError(null);

    try {
      if (mode === "symbols") {
        const response = await api.searchSymbols(q, types, fuzzy);
        setSymbols(response.results);
        setFiles([]);
        setTotal(response.total);
      } else {
        const response = await api.searchFiles(q);
        setFiles(response.results);
        setSymbols([]);
        setTotal(response.total);
      }
      setSearched({ query: q, mode });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const shown = searched?.mode === "symbols" ? symbols.length : files.length;

  return (
    <>
      <h1>Search</h1>
      <p className="lead">Find a class, function, or file in everything you’ve added.</p>

      <form className="form" onSubmit={onSubmit}>
        <div className="search-row">
          <select
            aria-label="Search for"
            value={mode}
            onChange={(event) => setMode(event.target.value as Mode)}
          >
            <option value="symbols">Symbols</option>
            <option value="files">Files</option>
          </select>
          <input
            type="search"
            aria-label="Search query"
            placeholder={mode === "symbols" ? "TaskManager" : "utils/helpers"}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" className="button" disabled={loading || !query.trim()}>
            {loading ? "Searching…" : "Search"}
          </button>
        </div>

        {mode === "symbols" && (
          <fieldset className="filters">
            <legend>Filter</legend>
            {SYMBOL_TYPES.map((type) => (
              <label key={type} className="check">
                <input
                  type="checkbox"
                  checked={types.includes(type)}
                  onChange={() => toggleType(type)}
                />
                {type}
              </label>
            ))}
            <label className="check">
              <input
                type="checkbox"
                checked={fuzzy}
                onChange={(event) => setFuzzy(event.target.checked)}
              />
              Match typos
            </label>
          </fieldset>
        )}
      </form>

      {error && <ErrorMessage message={error} />}

      {searched && !error && (
        <section aria-live="polite">
          <p className="muted">
            {total === 0
              ? `No ${searched.mode} match “${searched.query}”. Check the spelling, or add more code on the Upload page.`
              : `Showing ${shown} of ${total} results for “${searched.query}”.`}
          </p>

          {symbols.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>File</th>
                    <th>Line</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {symbols.map((symbol, index) => (
                    <tr key={`${symbol.file_path}:${symbol.line}:${index}`}>
                      <td className="path">{symbol.name}</td>
                      <td>{symbol.type}</td>
                      <td>
                        <FilePathLink path={symbol.file_path} />
                      </td>
                      <td>{symbol.line}</td>
                      <td>{symbol.match}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {files.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Language</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.path}>
                      <td>
                        <FilePathLink path={file.path} />
                      </td>
                      <td>{file.language ?? "–"}</td>
                      <td>{file.match}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}
