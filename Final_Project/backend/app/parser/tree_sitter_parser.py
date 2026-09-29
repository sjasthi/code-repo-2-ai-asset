from tree_sitter import Language, Parser
import tree_sitter_python as tree_sitter_python


class PythonParser:
    def __init__(self):
        self.language = Language(tree_sitter_python.language())
        self.parser = Parser(self.language)

    def parse(self, source_code: str):
        source_bytes = source_code.encode("utf-8")
        tree = self.parser.parse(source_bytes)

        return tree