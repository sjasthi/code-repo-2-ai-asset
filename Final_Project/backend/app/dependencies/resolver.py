
from pathlib import Path


class ImportResolver:
    """
    Resolve imports to files inside a project root.
    External packages are left unresolved.
    """

    JS_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx"]

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def resolve(self, source_file: str, import_target: str,
                language: str):
        source = Path(source_file)

        if not source.is_absolute():
            source = self.project_root / source

        # Do not resolve package names such as "fastapi" or "react".
        if not import_target.startswith("."):
            if language.lower() == "python":
                candidate = self.project_root / (
                    import_target.replace(".", "/") + ".py"
                )
                if candidate.is_file():
                    return candidate.relative_to(
                        self.project_root
                    ).as_posix()

            return None

        candidate = (source.parent / import_target).resolve()

        # Prevent imports from resolving outside the project root.
        try:
            candidate.relative_to(self.project_root)
        except ValueError:
            return None

        candidates = [candidate]

        if language.lower() in ("javascript", "typescript", "js", "ts"):
            candidates.extend(
                Path(str(candidate) + ext)
                for ext in self.JS_EXTENSIONS
            )
            candidates.extend(
                candidate / ("index" + ext)
                for ext in self.JS_EXTENSIONS
            )
        else:
            candidates.append(Path(str(candidate) + ".py"))
            candidates.append(candidate / "__init__.py")

        for path in candidates:
            if path.is_file():
                return path.relative_to(
                    self.project_root
                ).as_posix()

        return None
