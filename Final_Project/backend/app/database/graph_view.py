"""
FP8: graph data for the frontend visualization.

Returns nodes and edges in a flat, Cytoscape-friendly shape. File nodes
use their path as id ("file:<path>"), so the frontend can link a node
straight to the dependencies page. Symbol and call-target nodes use
Neo4j's elementId.
"""

UPLOADS_PROJECT = "uploads"
GITHUB_PREFIX = "github.com/"

# Neo4j label -> type sent to the frontend.
SYMBOL_TYPES = {
    "Class": "class",
    "Function": "function",
    "Method": "method",
    "Variable": "variable",
}


# One row per project: each imported GitHub repository, plus "uploads"
# for files added on the Upload page.
PROJECTS = """
MATCH (f:File)
WITH split(f.path, '/') AS parts
WITH CASE
    WHEN parts[0] = 'github.com' AND size(parts) > 3
    THEN parts[0] + '/' + parts[1] + '/' + parts[2] + '/'
    ELSE $uploads
END AS project
RETURN project, count(*) AS files
ORDER BY project
"""

# Files in a project. $project is null for every file.
PROJECT_FILES = """
MATCH (f:File)
WHERE $project IS NULL
   OR ($project = $uploads AND NOT f.path STARTS WITH $github)
   OR ($project <> $uploads AND f.path STARTS WITH $project)
RETURN f.path AS path, f.language AS language
ORDER BY path
LIMIT $limit
"""

PROJECT_FILE_COUNT = """
MATCH (f:File)
WHERE $project IS NULL
   OR ($project = $uploads AND NOT f.path STARTS WITH $github)
   OR ($project <> $uploads AND f.path STARTS WITH $project)
RETURN count(f) AS total
"""

# A file plus every file within {depth} imports of it, in either
# direction. {depth} is a validated int; Cypher can't parameterize it.
NEIGHBOURHOOD_FILES = """
MATCH (center:File {{path: $file}})
OPTIONAL MATCH (center)-[:IMPORTS*1..{depth}]-(other:File)
WITH center, collect(DISTINCT other) AS others
UNWIND [center] + others AS f
WITH DISTINCT f
RETURN f.path AS path, f.language AS language
ORDER BY path = $file DESC, path
LIMIT $limit
"""

IMPORT_EDGES = """
MATCH (a:File)-[r:IMPORTS]->(b:File)
WHERE a.path IN $paths AND b.path IN $paths
RETURN a.path AS source, b.path AS target, r.line AS line
"""

FILE_SYMBOLS = """
MATCH (f:File)-[:CONTAINS]->(s)
WHERE f.path IN $paths
RETURN elementId(s) AS id,
       labels(s)[0] AS label,
       s.name AS name,
       s.line AS line,
       f.path AS file_path
"""

# Calls point at a Function node by name. It may be a function defined
# in a stored file, or an unresolved name with no file_path.
FILE_CALLS = """
MATCH (f:File)-[r:CALLS]->(fn:Function)
WHERE f.path IN $paths
RETURN f.path AS source,
       elementId(fn) AS id,
       fn.name AS name,
       fn.file_path AS file_path,
       fn.line AS line,
       count(r) AS calls
"""


def file_node_id(path: str) -> str:
    return f"file:{path}"


def file_label(path: str) -> str:
    return path.rsplit("/", 1)[-1]


class GraphView:

    def __init__(self, database):
        self.db = database

    def projects(self):
        return [
            {
                "id": row["project"],
                "label": (
                    "Uploaded files"
                    if row["project"] == UPLOADS_PROJECT
                    else row["project"].rstrip("/")
                ),
                "files": row["files"],
            }
            for row in self.db.execute_query(
                PROJECTS, {"uploads": UPLOADS_PROJECT}
            )
        ]

    def graph(
        self,
        project: str | None = None,
        file: str | None = None,
        depth: int = 1,
        include_symbols: bool = False,
        include_calls: bool = False,
        limit: int = 500,
    ):
        scope = {
            "project": project,
            "uploads": UPLOADS_PROJECT,
            "github": GITHUB_PREFIX,
        }

        # Ask for one extra row to learn whether the result is cut off.
        if file:
            rows = self.db.execute_query(
                NEIGHBOURHOOD_FILES.format(depth=int(depth)),
                {"file": file, "limit": limit + 1},
            )
        else:
            rows = self.db.execute_query(
                PROJECT_FILES, {**scope, "limit": limit + 1}
            )

        truncated = len(rows) > limit
        rows = rows[:limit]

        # Only count when cut off; None means "more than limit" for a
        # neighbourhood, which has no cheap count.
        total = len(rows)
        if truncated:
            total = (
                None if file
                else self.db.execute_query(PROJECT_FILE_COUNT, scope)[0]["total"]
            )
        paths = [row["path"] for row in rows]

        nodes = {
            file_node_id(row["path"]): {
                "id": file_node_id(row["path"]),
                "type": "file",
                "label": file_label(row["path"]),
                "path": row["path"],
                "language": row.get("language"),
            }
            for row in rows
        }
        edges = []

        if paths:
            for row in self.db.execute_query(IMPORT_EDGES, {"paths": paths}):
                edges.append({
                    "id": f"imports:{row['source']}->{row['target']}",
                    "source": file_node_id(row["source"]),
                    "target": file_node_id(row["target"]),
                    "type": "imports",
                    "line": row.get("line"),
                })

        if paths and include_symbols:
            for row in self.db.execute_query(FILE_SYMBOLS, {"paths": paths}):
                symbol_type = SYMBOL_TYPES.get(row["label"])
                if not symbol_type:
                    continue

                nodes[row["id"]] = {
                    "id": row["id"],
                    "type": symbol_type,
                    "label": row["name"],
                    "path": row["file_path"],
                    "line": row.get("line"),
                }
                edges.append({
                    "id": f"contains:{row['id']}",
                    "source": file_node_id(row["file_path"]),
                    "target": row["id"],
                    "type": "contains",
                })

        if paths and include_calls:
            for row in self.db.execute_query(FILE_CALLS, {"paths": paths}):
                # Reuse the symbol node when the call resolved to one.
                nodes.setdefault(row["id"], {
                    "id": row["id"],
                    "type": "function" if row.get("file_path") else "external",
                    "label": row["name"],
                    "path": row.get("file_path"),
                    "line": row.get("line"),
                })
                edges.append({
                    "id": f"calls:{row['source']}->{row['id']}",
                    "source": file_node_id(row["source"]),
                    "target": row["id"],
                    "type": "calls",
                    "count": row.get("calls", 1),
                })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "files": len(paths),
            "total_files": total,
            "truncated": truncated,
        }
