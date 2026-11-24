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

// FP8 graph view (GET /graph, GET /graph/projects).

export type GraphNodeType =
  | "file"
  | "class"
  | "function"
  | "method"
  | "variable"
  | "external";

export type GraphEdgeType = "imports" | "contains" | "calls";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  path?: string | null;
  language?: string | null;
  line?: number | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  line?: number | null;
  count?: number | null;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  files: number;
  // null when centred on a file and cut off: "more than `files`".
  total_files: number | null;
  truncated: boolean;
  nodes_truncated?: boolean;
  edges_truncated?: boolean;
}

export interface GraphProject {
  id: string;
  label: string;
  files: number;
}

export interface GraphOptions {
  project?: string;
  file?: string;
  depth?: number;
  includeSymbols?: boolean;
  includeCalls?: boolean;
  limit?: number;
}
export interface DependencySearchResponse {
  query: string;
  target_type: string;
  name: string;
  file_path: string;
  imports: string[];
  imported_by: string[];
  calls: { name: string; line: number | null }[];
  called_by: { file_path: string; line: number | null }[];
  call_matching: string;
}
