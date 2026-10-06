from .typescript_parser import TypeScriptParser


class TypeScriptSymbolExtractor:
    def __init__(self):
        self.parser = TypeScriptParser()

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
        if node.type in (
            "class_declaration",
            "abstract_class_declaration"
        ):
            name_node = node.child_by_field_name("name")

            if name_node:
                symbols.append({
                    "type": "class",
                    "name": self._get_text(
                        name_node,
                        source_bytes
                    ),
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")

            if name_node:
                symbols.append({
                    "type": "function",
                    "name": self._get_text(
                        name_node,
                        source_bytes
                    ),
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        elif node.type == "method_definition":
            name_node = node.child_by_field_name("name")

            if name_node:
                symbols.append({
                    "type": "method",
                    "name": self._get_text(
                        name_node,
                        source_bytes
                    ),
                    "file_path": file_path,
                    "line": node.start_point[0] + 1
                })

        elif node.type in (
            "lexical_declaration",
            "variable_declaration"
        ):
            self._extract_variables(
                node,
                source_bytes,
                file_path,
                symbols
            )

        for child in node.children:
            self._walk_tree(
                child,
                source_bytes,
                file_path,
                symbols
            )

    def _extract_variables(
        self,
        node,
        source_bytes,
        file_path,
        symbols
    ):
        for child in node.children:

            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")

                if name_node and name_node.type == "identifier":
                    symbols.append({
                        "type": "variable",
                        "name": self._get_text(
                            name_node,
                            source_bytes
                        ),
                        "file_path": file_path,
                        "line": node.start_point[0] + 1
                    })

    def _get_text(self, node, source_bytes):
        return source_bytes[
            node.start_byte:node.end_byte
        ].decode("utf-8")