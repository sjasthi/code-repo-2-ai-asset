from .tree_sitter_parser import PythonParser


class PythonSymbolExtractor:
    def __init__(self):
        self.parser = PythonParser()

    def extract_symbols(self, source_code: str, file_path: str):
        tree = self.parser.parse(source_code)
        symbols = []

        self._walk_tree(
            tree.root_node,
            source_code,
            file_path,
            symbols
        )

        return symbols

    def _walk_tree(
        self,
        node,
        source_code,
        file_path,
        symbols
    ):
        # Detect classes
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")

            if name_node:
                name = source_code[
                    name_node.start_byte:name_node.end_byte
                ]

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
                name = source_code[
                    name_node.start_byte:name_node.end_byte
                ]

                symbol_type = self._get_function_type(node)

                symbols.append({
                    "type": symbol_type,
                    "name": name,
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        # Detect variables
        elif node.type == "assignment":
            left_node = node.child_by_field_name("left")

            if left_node and left_node.type == "identifier":
                name = source_code[
                    left_node.start_byte:left_node.end_byte
                ]

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
                source_code,
                file_path,
                symbols
            )

    def _get_function_type(self, node):
        parent = node.parent

        if parent and parent.type == "block":
            grandparent = parent.parent

            if grandparent and grandparent.type == "class_definition":
                return "method"

        return "function"