from .tree_sitter_parser import PythonParser


class PythonSymbolExtractor:
    def __init__(self):
        self.parser = PythonParser()

    def extract_symbols(self, source_code: str, file_path: str):
        tree = self.parser.parse(source_code)
        source_bytes = source_code.encode("utf-8")
        symbols = []

        self._walk_tree(
            tree.root_node,
            source_bytes,
            file_path,
            symbols
        )

        return symbols

    def _walk_tree(
        self,
        node,
        source_bytes,
        file_path,
        symbols
    ):
        # Detect classes
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")

            if name_node:
                name = source_bytes[
                    name_node.start_byte:name_node.end_byte
                ].decode("utf-8")

                symbols.append({
                    "type": "class",
                    "name": name,
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        # Detect functions and methods
        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")

            if name_node:
                name = source_bytes[
                    name_node.start_byte:name_node.end_byte
                ].decode("utf-8")

                symbol_type = self._get_function_type(node)

                symbols.append({
                    "type": symbol_type,
                    "name": name,
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        # Detect variables
        elif node.type in ("assignment", "augmented_assignment"):
            left_node = node.child_by_field_name("left")

            if left_node:
                for identifier_node in self._extract_identifiers(left_node):
                    name = source_bytes[
                        identifier_node.start_byte:identifier_node.end_byte
                    ].decode("utf-8")

                    symbols.append({
                        "type": "variable",
                        "name": name,
                        "file_path": file_path,
                        "line": node.start_point[0] + 1
                    })

        # Continue walking through child nodes
        for child in node.children:
            self._walk_tree(
                child,
                source_bytes,
                file_path,
                symbols
            )

    def _extract_identifiers(self, node):
        if node.type == "identifier":
            return [node]

        if node.type in ("pattern_list", "tuple_pattern", "list_pattern"):
            identifiers = []

            for child in node.children:
                identifiers.extend(self._extract_identifiers(child))

            return identifiers

        return []

    def _get_function_type(self, node):
        parent = node.parent

        if parent and parent.type == "block":
            grandparent = parent.parent

            if grandparent and grandparent.type == "class_definition":
                return "method"

        return "function"