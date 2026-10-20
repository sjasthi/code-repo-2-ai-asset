
# Symbol type from the parser -> Neo4j node label.
SYMBOL_LABELS = {
    "class": "Class",
    "function": "Function",
    "method": "Method",
    "variable": "Variable",
}


class DependencyGraphBuilder:
    """
    Stores source files, symbols, and their import/call relationships
    in Neo4j. Uses the existing Neo4jConnection from FP4.
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
        Unresolved calls point to a Function node by name.
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

    def clear_stale_symbols(self, file_path: str, symbols: list):
        """
        Remove symbols previously stored for this file that are no longer
        present in the latest parse.
        """

        keep = [
            [SYMBOL_LABELS[symbol["type"]], symbol["name"], symbol["line"]]
            for symbol in symbols
            if symbol["type"] in SYMBOL_LABELS
        ]

        query = """
        MATCH (:File {path: $file_path})-[:CONTAINS]->(symbol)
        WHERE NOT [labels(symbol)[0], symbol.name, symbol.line] IN $keep
        DETACH DELETE symbol
        """

        return self.db.execute_query(query, {
            "file_path": file_path,
            "keep": keep,
        })

    def store_symbol(self, symbol: dict):
        """
        Store one symbol and connect it to the file where it is defined.
        The symbol must contain type, name, file_path, and line.
        """

        label = SYMBOL_LABELS.get(symbol["type"])

        # Skip symbol types not supported by the current graph schema.
        if not label:
            return False

        query = f"""
        MERGE (f:File {{path: $file_path}})
        MERGE (s:{label} {{
            name: $name,
            file_path: $file_path,
            line: $line
        }})
        MERGE (f)-[:CONTAINS]->(s)
        """

        self.db.execute_query(query, {
            "file_path": symbol["file_path"],
            "name": symbol["name"],
            "line": symbol["line"],
        })

        return True

    def store_symbols(self, file_path: str, symbols: list):
        """
        Remove stale symbols, then store the symbols from the latest parse.
        Returns the number of symbols stored.
        """

        self.clear_stale_symbols(file_path, symbols)

        return sum(
            1 for symbol in symbols
            if self.store_symbol(symbol)
        )

    def store_dependencies(
        self,
        file_path: str,
        language: str,
        dependencies: list,
    ):
        """
        Store the file and its resolved import and function-call relationships.
        """

        self.store_file(file_path, language)

        stored = 0

        for dependency in dependencies:
            if dependency["type"] == "import":
                target_path = dependency.get("resolved_target")

                # Only create IMPORTS edges for imports resolved to local files.
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
