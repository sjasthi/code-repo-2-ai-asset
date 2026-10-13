
# What files does a file import?
FILE_IMPORTS = """
MATCH (source:File {path: $file_path})-[:IMPORTS]->(target:File)
RETURN target.path AS imported_file
ORDER BY imported_file
"""

# What files import a given file?
FILE_IMPORTED_BY = """
MATCH (source:File)-[:IMPORTS]->(target:File {path: $file_path})
RETURN source.path AS importing_file
ORDER BY importing_file
"""

# Show direct and indirect dependencies up to 5 edges away.
DEPENDENCY_CHAIN = """
MATCH path = (source:File {path: $file_path})-[:IMPORTS*1..5]->(target:File)
RETURN [node IN nodes(path) | node.path] AS dependency_path
"""

# Show function calls recorded for a source file.
FILE_CALLS = """
MATCH (source:File {path: $file_path})-[:CALLS]->(target:Function)
RETURN target.name AS function_name, r.line AS line
ORDER BY line
"""

# Show the graph's node and relationship counts.
GRAPH_SUMMARY = """
MATCH (n)
WITH count(n) AS node_count
MATCH ()-[r]->()
RETURN node_count, count(r) AS relationship_count
"""
