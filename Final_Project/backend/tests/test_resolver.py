import pytest

from app.dependencies.resolver import ImportResolver


@pytest.fixture
def project(tmp_path):
    files = [
        "app.py",
        "src/pkg/__init__.py",
        "src/pkg/models.py",
        "src/pkg/sessions.py",
        "src/pkg/utils.py",
        "src/pkg/compat.py",
        "src/pkg/sub/__init__.py",
        "src/pkg/sub/helper.py",
        "web/main.js",
        "web/lib/util.ts",
        "web/widgets/index.js",
    ]

    for file in files:
        path = tmp_path / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")

    return ImportResolver(str(tmp_path))


@pytest.mark.parametrize("source, target, expected", [
    # from .models import Request
    ("src/pkg/sessions.py", ".models", "src/pkg/models.py"),
    # from ..compat import json
    ("src/pkg/sub/helper.py", "..compat", "src/pkg/compat.py"),
    # from . import utils  (utils is a module)
    ("src/pkg/sessions.py", ".utils", "src/pkg/utils.py"),
    # from . import Session  (Session is defined in __init__.py)
    ("src/pkg/sessions.py", ".Session", "src/pkg/__init__.py"),
    # from .models.User import x  (User is a class in models.py)
    ("src/pkg/sessions.py", ".models.User", "src/pkg/models.py"),
    # from .sub import helper
    ("src/pkg/sessions.py", ".sub", "src/pkg/sub/__init__.py"),
    # from .. import Session
    ("src/pkg/sub/helper.py", "..Session", "src/pkg/__init__.py"),
])
def test_resolves_python_relative_imports(project, source, target, expected):

    assert project.resolve(source, target, "python") == expected


@pytest.mark.parametrize("source, target, expected", [
    ("src/pkg/sessions.py", "app", "app.py"),
    ("app.py", "src.pkg", "src/pkg/__init__.py"),
    ("app.py", "src.pkg.models", "src/pkg/models.py"),
])
def test_resolves_python_absolute_imports(project, source, target, expected):

    assert project.resolve(source, target, "python") == expected


@pytest.mark.parametrize("source, target", [
    # Standard library / external packages.
    ("app.py", "os"),
    ("app.py", "fastapi.routing"),
    # Too many dots climbs above the project root.
    ("src/pkg/sessions.py", "....outside"),
])
def test_unresolvable_python_imports_return_none(project, source, target):

    assert project.resolve(source, target, "python") is None


def test_missing_relative_module_falls_back_to_its_package(project):

    # The names could be defined in the package's __init__.py.
    assert project.resolve(
        "src/pkg/sessions.py", ".missing.thing", "python"
    ) == "src/pkg/__init__.py"


@pytest.mark.parametrize("target, expected", [
    ("./lib/util", "web/lib/util.ts"),
    ("./lib/util.ts", "web/lib/util.ts"),
    ("./widgets", "web/widgets/index.js"),
])
def test_resolves_javascript_imports(project, target, expected):

    assert project.resolve("web/main.js", target, "javascript") == expected


@pytest.mark.parametrize("target", ["react", "./missing", "../../../outside"])
def test_unresolvable_javascript_imports_return_none(project, target):

    assert project.resolve("web/main.js", target, "javascript") is None
