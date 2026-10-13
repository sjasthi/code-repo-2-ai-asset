
import ast
import re


class DependencyExtractor:
    """
    Extract basic import statements and function calls
    from Python, JavaScript, and TypeScript source code.
    """

    def extract(self, source_code: str, file_path: str, language: str):
        language = language.lower()

        if language == "python":
            return self._extract_python(source_code, file_path)

        if language in ("javascript", "typescript", "js", "ts"):
            return self._extract_javascript(source_code, file_path)

        raise ValueError(f"Unsupported language: {language}")

    def _extract_python(self, source_code: str, file_path: str):
        dependencies = []

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            return dependencies

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append({
                        "type": "import",
                        "source_file": file_path,
                        "target": alias.name,
                        "line": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""

                dependencies.append({
                    "type": "import",
                    "source_file": file_path,
                    "target": module,
                    "line": node.lineno,
                })

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                else:
                    continue

                dependencies.append({
                    "type": "call",
                    "source_file": file_path,
                    "target": call_name,
                    "line": node.lineno,
                })

        return dependencies

    def _extract_javascript(self, source_code: str, file_path: str):
        dependencies = []

        # Static ES module imports:
        # import x from "./x.js"
        # import "./setup.js"
        # export { x } from "./x.js"
        import_pattern = re.compile(
            r"""(?:\bimport\s+(?:[^;]*?\s+from\s+)?|\bexport\s+[^;]*?\s+from\s+)["']([^"']+)["']"""
        )

        # CommonJS imports:
        # require("./helpers")
        require_pattern = re.compile(
            r"""\brequire\s*\(\s*["']([^"']+)["']\s*\)"""
        )

        for pattern in (import_pattern, require_pattern):
            for match in pattern.finditer(source_code):
                line = source_code.count("\n", 0, match.start()) + 1

                dependencies.append({
                    "type": "import",
                    "source_file": file_path,
                    "target": match.group(1),
                    "line": line,
                })

        # Basic call detection: hello(), object.hello(), etc.
        # This records call names; it does not resolve every call target.
        call_pattern = re.compile(
            r"\b([A-Za-z_$][\w$]*)\s*\("
        )

        keywords = {
            "if", "for", "while", "switch", "catch",
            "function", "return", "new", "typeof",
            "import", "require", "super",
        }

        for match in call_pattern.finditer(source_code):
            call_name = match.group(1)

            if call_name in keywords:
                continue

            line = source_code.count("\n", 0, match.start()) + 1

            dependencies.append({
                "type": "call",
                "source_file": file_path,
                "target": call_name,
                "line": line,
            })

        return dependencies
