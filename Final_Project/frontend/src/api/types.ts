// Types mirror the FastAPI responses in backend/app/main.py.

export type SymbolType = "class" | "function" | "method" | "variable";

export interface Dependency {
  type: string;
  target: string;
  resolved_target?: string | null;
  [key: string]: unknown;
}

export interface AnalyzeResponse {
  file: string;
  language: string;
  dependencies_found: number;
  relationships_stored: number;
  symbols_stored: number;
  dependencies: Dependency[];
}

export interface RepositoryImportResponse {
  status: string;
  repository: string;
  branch: string;
  files_analyzed: number;
  symbols_stored: number;
  dependencies_found: number;
  relationships_stored: number;
  skipped_files: unknown;
  files_with_syntax_errors: number;
  graph_path_prefix: string;
}

export interface SymbolSearchResult {
  type: string;
  name: string;
  file_path: string;
  line: number;
  score: number;
  match: "exact" | "prefix" | "contains" | "fuzzy";
}

export interface FileSearchResult {
  path: string;
  language: string | null;
  match: "exact" | "prefix" | "contains";
}

export interface SearchResponse<T> {
  query: string;
  total: number;
  limit: number;
  offset: number;
  results: T[];
}

export interface ImportedFile {
  imported_file: string;
}

export interface ImportingFile {
  importing_file: string;
}

export interface Neo4jHealth {
  status: string;
  neo4j: string;
}
