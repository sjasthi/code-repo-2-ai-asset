
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

        if language.lower() == "python":
            return self._resolve_python(source, import_target)

        # Do not resolve package names such as "react".
        if not import_target.startswith("."):
            return None

        candidate = (source.parent / import_target).resolve()

        candidates = [candidate]
        candidates.extend(
            Path(str(candidate) + ext)
            for ext in self.JS_EXTENSIONS
        )
        candidates.extend(
            candidate / ("index" + ext)
            for ext in self.JS_EXTENSIONS
        )

        return self._first_file(candidates)

    def _resolve_python(self, source: Path, import_target: str):
        """
        Resolve "pkg.module" from the project root, and relative imports
        like ".module" (same package) or "..module" (parent package)
        from the importing file's package.
        """
        module = import_target.lstrip(".")
        level = len(import_target) - len(module)

        if level:
            base = source.parent

            # One dot is the current package; each extra dot goes up one.
            for _ in range(level - 1):
                base = base.parent
        else:
            # Absolute imports of external packages ("fastapi") simply
            # fail to match a local file below.
            base = self.project_root

        parts = module.split(".") if module else []

        # "from . import utils" is recorded as ".utils", but utils may be a
        # function or class defined in the package, not a module. Fall back
        # to shorter module paths, down to the package itself for relative
        # imports (an absolute import never resolves to the project root).
        shortest = 0 if level else 1

        for length in range(len(parts), shortest - 1, -1):
            candidate = base.joinpath(*parts[:length])

            path = self._first_file([
                candidate.with_name(candidate.name + ".py") if length else None,
                candidate / "__init__.py",
            ])

            if path:
                return path

        return None

    def _first_file(self, candidates):
        for path in candidates:
            if path is None:
                continue

            path = path.resolve()

            # Prevent imports from resolving outside the project root.
            try:
                relative = path.relative_to(self.project_root)
            except ValueError:
                continue

            if path.is_file():
                return relative.as_posix()

        return None
