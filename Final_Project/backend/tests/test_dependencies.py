
from app.dependencies.extractor import DependencyExtractor


def test_extract_python_import():
    source = """
import os
from pathlib import Path
"""

    extractor = DependencyExtractor()
    dependencies = extractor.extract(
        source, "app.py", "python"
    )

    imports = [
        item for item in dependencies
        if item["type"] == "import"
    ]

    targets = [item["target"] for item in imports]

    assert "os" in targets
    assert "pathlib" in targets


def test_extract_python_function_call():
    source = """
def greet():
    print("Hello")

greet()
"""

    extractor = DependencyExtractor()
    dependencies = extractor.extract(
        source, "app.py", "python"
    )

    calls = [
        item["target"] for item in dependencies
        if item["type"] == "call"
    ]

    assert "greet" in calls
    assert "print" in calls


def test_extract_javascript_import():
    source = """
import { greet } from "./helpers.js";
const helpers = require("./other.js");
"""

    extractor = DependencyExtractor()
    dependencies = extractor.extract(
        source, "app.js", "javascript"
    )

    imports = [
        item["target"] for item in dependencies
        if item["type"] == "import"
    ]

    assert "./helpers.js" in imports
    assert "./other.js" in imports


def test_extract_javascript_function_call():
    source = """
function greet() {}
greet();
"""

    extractor = DependencyExtractor()
    dependencies = extractor.extract(
        source, "app.js", "javascript"
    )

    calls = [
        item["target"] for item in dependencies
        if item["type"] == "call"
    ]

    assert "greet" in calls


def test_invalid_python_returns_no_dependencies():
    extractor = DependencyExtractor()

    dependencies = extractor.extract(
        "def broken(:",
        "broken.py",
        "python",
    )

    assert dependencies == []


def test_unsupported_language_raises_error():
    extractor = DependencyExtractor()

    try:
        extractor.extract("", "file.java", "java")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def import_targets(source):
    dependencies = DependencyExtractor().extract(
        source, "pkg/sessions.py", "python"
    )

    return [
        item["target"] for item in dependencies
        if item["type"] == "import"
    ]


def test_extract_python_relative_import_keeps_dots():

    assert import_targets("from .models import Request\n") == [".models"]
    assert import_targets("from ..compat import json\n") == ["..compat"]


def test_extract_python_bare_relative_import_records_each_name():

    assert import_targets("from . import utils, hooks\n") == [
        ".utils",
        ".hooks",
    ]
