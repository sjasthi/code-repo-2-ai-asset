
class DependencyGraphBuilder:
    """
    Stores source files and their import/call relationships in Neo4j.
    Uses the existing Neo4jConnection from FP4.
    """

    def __init__(self, neo4j_connection):
        self.db = neo4j_connection

    def store_file(self, file_path: str, language: str):
        query = """
        MERGE (f:File {path: $path})
        SET f.language = $language
        RETURN f.path AS path
        """

        return self.db.execute_query(query, {
            "path": file_path,
            "language": language,
        })

    def store_import(self, source_file: str, target_file: str, line: int):
        query = """
        MERGE (source:File {path: $source_file})
        MERGE (target:File {path: $target_file})
        MERGE (source)-[r:IMPORTS]->(target)
        SET r.line = $line
        RETURN source.path AS source, target.path AS target
        """

        return self.db.execute_query(query, {
            "source_file": source_file,
            "target_file": target_file,
            "line": line,
        })

    def store_call(self, source_file: str, function_name: str, line: int):
        """
        Record a potential call from a file to a named function.

        The target is marked as an unresolved Function node if its
        declaration has not been identified. This is an initial
        representation; later work can resolve calls to declarations.
        """
        query = """
        MERGE (source:File {path: $source_file})
        MERGE (target:Function {name: $function_name})
        MERGE (source)-[r:CALLS]->(target)
        SET r.line = $line,
            r.resolution = 'unresolved'
        RETURN source.path AS source, target.name AS target
        """

        return self.db.execute_query(query, {
            "source_file": source_file,
            "function_name": function_name,
            "line": line,
        })

    def store_dependencies(self, file_path: str, language: str,
                           dependencies: list):
        self.store_file(file_path, language)

        stored = 0

        for dependency in dependencies:
            if dependency["type"] == "import":
                target = dependency["target"]

                # External packages are not local File nodes.
                # For now, only create IMPORTS edges for relative imports
                # or Python-style module names resolved by the caller.
                if target:
                    target_path = dependency.get("resolved_target")

                    if target_path:
                        self.store_import(
                            file_path,
                            target_path,
                            dependency["line"],
                        )
                        stored += 1

            elif dependency["type"] == "call":
                self.store_call(
                    file_path,
                    dependency["target"],
                    dependency["line"],
                )
                stored += 1

        return stored
