from functools import lru_cache

import tree_sitter_language_pack
from tree_sitter import Parser, Query, QueryCursor


# Extra patterns for definitions the bundled tags queries miss.
SUPPLEMENTAL_QUERIES = {
    "go": """
    (type_spec
      name: (type_identifier) @name
      type: (struct_type)) @definition.class

    (type_spec
      name: (type_identifier) @name
      type: (interface_type)) @definition.interface
    """,
    "cpp": """
    (struct_specifier name: (type_identifier) @name) @definition.class

    (field_declaration_list
      (function_definition
        declarator: (function_declarator
          declarator: (field_identifier) @name)) @definition.method)

    (function_definition
      declarator: (function_declarator
        declarator: (qualified_identifier
          name: (identifier) @name))) @definition.method
    """,
}

# When one node matches several kinds, keep the more specific one,
# e.g. a Rust function inside an impl block is a method, not a function.
KIND_PRIORITY = {
    "method": 0,
    "class": 1,
    "interface": 1,
    "module": 1,
    "macro": 1,
    "type": 2,
    "function": 3,
}


@lru_cache(maxsize=None)
def _load(language: str):
    tree_sitter_language = tree_sitter_language_pack.get_language(language)

    query_source = tree_sitter_language_pack.get_tags_query(language) or ""
    query_source += SUPPLEMENTAL_QUERIES.get(language, "")

    return (
        Parser(tree_sitter_language),
        Query(tree_sitter_language, query_source)
    )


class TagsSymbolExtractor:
    """
    Language-agnostic symbol extractor driven by tree-sitter tags queries.

    Each query marks definitions with captures like @definition.class
    and their names with @name, so one code path handles every language.
    """

    def __init__(self, language: str):
        self.language = language
        self.parser, self.query = _load(language)

    def extract_symbols(self, source_code: str, file_path: str):
        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)

        # Kept so callers can check tree.root_node.has_error.
        self.tree = tree

        # (start_byte, end_byte) of the definition node -> symbol
        found = {}

        for _, captures in QueryCursor(self.query).matches(tree.root_node):
            definition = self._get_definition(captures)
            names = captures.get("name")

            if not definition or not names:
                continue

            kind, node = definition
            key = (node.start_byte, node.end_byte)
            existing = found.get(key)

            if existing and KIND_PRIORITY.get(existing["type"], 9) <= KIND_PRIORITY.get(kind, 9):
                continue

            found[key] = {
                "type": kind,
                "name": self._get_text(names[0], source_bytes),
                "file_path": file_path,
                "line": node.start_point[0] + 1
            }

        return sorted(
            found.values(),
            key=lambda symbol: symbol["line"]
        )

    def _get_definition(self, captures):
        for capture_name, nodes in captures.items():
            if capture_name.startswith("definition."):
                return capture_name.split(".", 1)[1], nodes[0]

        return None

    def _get_text(self, node, source_bytes):
        return source_bytes[
            node.start_byte:node.end_byte
        ].decode("utf-8")
