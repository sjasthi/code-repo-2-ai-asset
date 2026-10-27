import type {
  AnalyzeResponse,
  FileSearchResult,
  ImportedFile,
  ImportingFile,
  Neo4jHealth,
  RepositoryImportResponse,
  SearchResponse,
  SymbolSearchResult,
  SymbolType,
} from "./types";

export const API_URL: string = (
  import.meta.env.VITE_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type Query = Record<string, string | number | boolean | string[] | undefined>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(API_URL + path);

  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined) continue;
    // Repeat the key for arrays: ?type=class&type=function
    for (const item of Array.isArray(value) ? value : [value]) {
      url.searchParams.append(key, String(item));
    }
  }

  return url.toString();
}

// FastAPI reports errors as {detail: string} or {detail: [{msg, loc}, ...]}.
function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d?.msg === "string" ? d.msg : JSON.stringify(d)))
      .join("; ");
  }
  return fallback;
}

async function request<T>(
  path: string,
  options: { method?: "GET" | "POST"; query?: Query; body?: unknown } = {},
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(buildUrl(path, options.query), {
      method: options.method ?? "GET",
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${API_URL}. Is it running?`,
      0,
    );
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(
      detailToMessage(detail, `Request failed (${response.status})`),
      response.status,
    );
  }

  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  neo4jHealth: () => request<Neo4jHealth>("/health/neo4j"),

  analyzeFile: (filePath: string, sourceCode: string, language: string) =>
    request<AnalyzeResponse>("/dependencies/analyze", {
      method: "POST",
      query: { language },
      body: { file_path: filePath, source_code: sourceCode },
    }),

  importRepository: (repositoryUrl: string, branch?: string) =>
    request<RepositoryImportResponse>("/repositories/import", {
      method: "POST",
      body: { repository_url: repositoryUrl, branch: branch || null },
    }),

  searchSymbols: (q: string, types: SymbolType[], fuzzy: boolean) =>
    request<SearchResponse<SymbolSearchResult>>("/search/symbols", {
      query: { q, type: types.length ? types : undefined, fuzzy, limit: 50 },
    }),

  searchFiles: (q: string) =>
    request<SearchResponse<FileSearchResult>>("/search/files", {
      query: { q, limit: 50 },
    }),

  fileImports: (filePath: string) =>
    request<ImportedFile[]>("/dependencies/imports", {
      query: { file_path: filePath },
    }),

  fileImportedBy: (filePath: string) =>
    request<ImportingFile[]>("/dependencies/imported-by", {
      query: { file_path: filePath },
    }),
};

// Extensions the backend can analyze for dependencies (see parser/registry.py).
const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  py: "python",
  pyi: "python",
  js: "javascript",
  jsx: "javascript",
  mjs: "javascript",
  cjs: "javascript",
  ts: "typescript",
  mts: "typescript",
  cts: "typescript",
};

export function detectLanguage(fileName: string): string | null {
  const extension = fileName.split(".").pop()?.toLowerCase() ?? "";
  return LANGUAGE_BY_EXTENSION[extension] ?? null;
}
