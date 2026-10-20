from functools import partial
from pathlib import Path

from .python_symbols import PythonSymbolExtractor
from .javascript_symbols import JavaScriptSymbolExtractor
from .typescript_symbols import TypeScriptSymbolExtractor
from .tags_symbols import TagsSymbolExtractor


class UnsupportedLanguageError(ValueError):
    pass


# Languages handled by the generic tags-query extractor.
# Adding one here (plus its extensions below) is all a new language needs.
TAGS_LANGUAGES = ("go", "rust", "java", "c", "cpp", "ruby")

# Canonical language name -> symbol extractor factory.
EXTRACTORS = {
    "python": PythonSymbolExtractor,
    "javascript": JavaScriptSymbolExtractor,
    "typescript": TypeScriptSymbolExtractor,
    **{
        language: partial(TagsSymbolExtractor, language)
        for language in TAGS_LANGUAGES
    },
}

# Short names accepted for the optional "language" field.
LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "golang": "go",
    "rs": "rust",
    "c++": "cpp",
    "rb": "ruby",
}

# File extension -> canonical language name.
EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".hxx": "cpp",
    ".rb": "ruby",
}


def detect_language(file_path: str, language: str | None = None) -> str:
    """
    Return the canonical language name for a file.

    An explicit language wins; otherwise the file extension is used.
    """
    if language:
        name = language.lower()
        name = LANGUAGE_ALIASES.get(name, name)

        if name not in EXTRACTORS:
            raise UnsupportedLanguageError(
                f"Unsupported language: {language}"
            )

        return name

    extension = Path(file_path).suffix.lower()

    if extension not in EXTENSIONS:
        raise UnsupportedLanguageError(
            f"Cannot detect language from file extension: '{extension}'"
        )

    return EXTENSIONS[extension]


def get_extractor(language: str):
    return EXTRACTORS[language]()


def extract_symbols(
    source_code: str,
    file_path: str,
    language: str | None = None
):
    language = detect_language(file_path, language)
    extractor = get_extractor(language)

    symbols = extractor.extract_symbols(source_code, file_path)
    tree = getattr(extractor, "tree", None)

    if tree is None:
        parser = getattr(extractor, "parser", None)
        parse_method = getattr(parser, "parse", None)

        if callable(parse_method):
            tree = parse_method(source_code)
    
    has_syntax_errors = (
        tree.root_node.has_error
        if tree is not None
        else False
    )
    return language, symbols, has_syntax_errors
