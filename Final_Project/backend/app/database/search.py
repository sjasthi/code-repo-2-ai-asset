import re


SYMBOL_FULLTEXT_INDEX = "symbol_name_fulltext"

# Search "type" filter -> Neo4j labels.
SYMBOL_TYPE_LABELS = {
    "class": ["Class"],
    "function": ["Function"],
    "method": ["Method"],
    "variable": ["Variable"],
}

LABEL_TO_TYPE = {
    "Class": "class",
    "Function": "function",
    "Method": "method",
    "Variable": "variable",
}

# Ranking tiers, best first.
MATCH_TIERS = {
    3: "exact",
    2: "prefix",
    1: "contains",
    0: "fuzzy",
}

# Characters with special meaning in Lucene query syntax.
LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')


def escape_lucene(term: str) -> str:
    return LUCENE_SPECIAL.sub(r"\\\1", term)


def build_lucene_query(query: str, fuzzy: bool = True) -> str:
    """
    Turn a user query into a Lucene query that finds exact, prefix,
    substring and (optionally) typo-tolerant matches.

    Multiple words must all match, e.g. "user serv" finds UserService
    only if both words match. Wildcard and fuzzy terms skip the
    analyzer, so terms are lowercased here to match the indexed tokens.
    """
    groups = []

    for word in query.lower().split():
        term = escape_lucene(word)

        clauses = [f"{term}^4", f"{term}*^2", f"*{term}*"]

        if fuzzy:
            # Short names drift into unrelated names at edit distance 2.
            distance = 1 if len(word) <= 4 else 2
            clauses.append(f"{term}~{distance}")

        groups.append("(" + " OR ".join(clauses) + ")")

    return " AND ".join(groups)


SEARCH_SYMBOLS = """
CALL db.index.fulltext.queryNodes($index, $lucene) YIELD node, score
WITH node, score, labels(node)[0] AS label, toLower(node.name) AS name
// Skip placeholder Function nodes created for unresolved CALLS.
WHERE node.file_path IS NOT NULL
  AND ($labels IS NULL OR label IN $labels)
  AND ($file_path IS NULL OR node.file_path = $file_path)
WITH node, score, label,
     CASE
         WHEN name = $term THEN 3
         WHEN name STARTS WITH $term THEN 2
         WHEN name CONTAINS $term THEN 1
         ELSE 0
     END AS tier
ORDER BY tier DESC, score DESC, node.name, node.file_path, node.line
WITH collect({
    label: label,
    name: node.name,
    file_path: node.file_path,
    line: node.line,
    score: score,
    tier: tier
}) AS matches
RETURN size(matches) AS total,
       matches[$offset..($offset + $limit)] AS page
"""

SEARCH_FILES = """
MATCH (f:File)
WHERE toLower(f.path) CONTAINS $term
WITH f,
     toLower(f.path) AS path,
     // File name without its directory, e.g. "main.py" for "app/main.py".
     toLower(last(split(f.path, "/"))) AS file_name
WITH f,
     CASE
         WHEN path = $term OR file_name = $term THEN 3
         WHEN file_name STARTS WITH $term THEN 2
         ELSE 1
     END AS tier
ORDER BY tier DESC, size(f.path), f.path
WITH collect({
    path: f.path,
    language: f.language,
    tier: tier
}) AS matches
RETURN size(matches) AS total,
       matches[$offset..($offset + $limit)] AS page
"""


class SymbolSearch:
    """
    Ranked symbol and file search over the dependency graph.
    """

    def __init__(self, neo4j_connection):
        self.db = neo4j_connection

    def search_symbols(
        self,
        query: str,
        types: list | None = None,
        file_path: str | None = None,
        fuzzy: bool = True,
        limit: int = 20,
        offset: int = 0,
    ):
        labels = None

        if types:
            labels = [
                label
                for symbol_type in types
                for label in SYMBOL_TYPE_LABELS[symbol_type]
            ]

        rows = self.db.execute_query(SEARCH_SYMBOLS, {
            "index": SYMBOL_FULLTEXT_INDEX,
            "lucene": build_lucene_query(query, fuzzy),
            "term": query.strip().lower(),
            "labels": labels,
            "file_path": file_path,
            "limit": limit,
            "offset": offset,
        })

        total, page = self._unpack(rows)

        return total, [
            {
                "type": LABEL_TO_TYPE.get(match["label"], match["label"]),
                "name": match["name"],
                "file_path": match["file_path"],
                "line": match["line"],
                "score": match["score"],
                "match": MATCH_TIERS[match["tier"]],
            }
            for match in page
        ]

    def search_files(self, query: str, limit: int = 20, offset: int = 0):
        rows = self.db.execute_query(SEARCH_FILES, {
            "term": query.strip().lower(),
            "limit": limit,
            "offset": offset,
        })

        total, page = self._unpack(rows)

        return total, [
            {
                "path": match["path"],
                "language": match["language"],
                "match": MATCH_TIERS[match["tier"]],
            }
            for match in page
        ]

    def _unpack(self, rows):
        if not rows:
            return 0, []

        return rows[0]["total"], rows[0]["page"]

# Dependency lookup for the FP9 unified search experience.
FILE_DEPENDENCIES = """
MATCH (target:File {path: $path})
OPTIONAL MATCH (target)-[:IMPORTS]->(imported:File)
OPTIONAL MATCH (importer:File)-[:IMPORTS]->(target)
OPTIONAL MATCH (target)-[call:CALLS]->(called:Function)
RETURN target.path AS path,
       collect(DISTINCT imported.path) AS imports,
       collect(DISTINCT importer.path) AS imported_by,
       collect(DISTINCT CASE WHEN called IS NULL THEN null ELSE {
           name: called.name, line: call.line
       } END) AS calls
"""

SYMBOL_DEPENDENCIES = """
MATCH (target)
WHERE target.name = $name
  AND target.file_path = $file_path
  AND labels(target)[0] IN ['Class', 'Function', 'Method', 'Variable']
OPTIONAL MATCH (defined_file:File)-[:CONTAINS]->(target)
OPTIONAL MATCH (importer:File)-[:IMPORTS]->(defined_file)
WITH target, defined_file, collect(DISTINCT importer.path) AS imported_by
OPTIONAL MATCH (caller:File)-[call:CALLS]->(called:Function {name: $name})
RETURN target.name AS name,
       labels(target)[0] AS label,
       defined_file.path AS file_path,
       imported_by,
       collect(DISTINCT CASE WHEN caller IS NULL THEN null ELSE {
           file_path: caller.path, line: call.line
       } END) AS called_by
"""


class DependencySearch:
    """Look up direct file and symbol dependencies stored in Neo4j."""

    def __init__(self, neo4j_connection):
        self.db = neo4j_connection

    def search_file(self, path: str):
        rows = self.db.execute_query(FILE_DEPENDENCIES, {"path": path})
        if not rows or rows[0].get("path") is None:
            return None
        row = rows[0]
        return {
            "target_type": "file",
            "name": path.rsplit("/", 1)[-1],
            "file_path": path,
            "imports": row.get("imports") or [],
            "imported_by": row.get("imported_by") or [],
            "calls": [item for item in (row.get("calls") or []) if item],
            "called_by": [],
            "call_matching": "",
        }

    def search_symbol(self, name: str, file_path: str, symbol_type: str):
        rows = self.db.execute_query(SYMBOL_DEPENDENCIES, {
            "name": name,
            "file_path": file_path,
        })
        if not rows or rows[0].get("name") is None:
            return None
        row = rows[0]
        called_by = [item for item in (row.get("called_by") or []) if item]
        return {
            "target_type": symbol_type,
            "name": name,
            "file_path": file_path,
            "imports": [],
            "imported_by": row.get("imported_by") or [],
            "calls": [],
            "called_by": called_by,
            "call_matching": (
                "Potential callers are matched by function name because "
                "the current graph stores CALLS relationships by name, "
                "not by a unique function definition."
                if symbol_type in ("function", "method") else ""
            ),
        }
