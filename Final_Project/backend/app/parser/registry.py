from pathlib import Path

from .python_symbols import PythonSymbolExtractor
from .javascript_symbols import JavaScriptSymbolExtractor
from .typescript_symbols import TypeScriptSymbolExtractor


class UnsupportedLanguageError(ValueError):
    pass


# Canonical language name -> symbol extractor class.
EXTRACTORS = {
    "python": PythonSymbolExtractor,
    "javascript": JavaScriptSymbolExtractor,
    "typescript": TypeScriptSymbolExtractor,
}

# Short names accepted for the optional "language" field.
LANGUAGE_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
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
    """
    Detect the language and extract symbols with the matching extractor.

    Returns (language, symbols).
    """
    language = detect_language(file_path, language)
    extractor = get_extractor(language)

    symbols = extractor.extract_symbols(source_code, file_path)

    return language, symbols
