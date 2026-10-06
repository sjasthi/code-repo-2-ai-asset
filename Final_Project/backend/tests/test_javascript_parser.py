from app.parser.javascript_symbols import JavaScriptSymbolExtractor


def test_identifies_javascript_class():

    source_code = """
class User {
}
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    assert symbols[0]["type"] == "class"
    assert symbols[0]["name"] == "User"


def test_identifies_javascript_function():

    source_code = """
function calculateTotal() {
}
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    assert symbols[0]["type"] == "function"
    assert symbols[0]["name"] == "calculateTotal"


def test_identifies_javascript_method():

    source_code = """
class User {
    login() {
    }
}
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    names = [symbol["name"] for symbol in symbols]

    assert "User" in names
    assert "login" in names

    method = next(
        symbol for symbol in symbols
        if symbol["name"] == "login"
    )

    assert method["type"] == "method"


def test_identifies_javascript_variable():

    source_code = """
const message = "Hello";
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    assert symbols[0]["type"] == "variable"
    assert symbols[0]["name"] == "message"


def test_includes_javascript_file_path():

    source_code = """
class User {
}
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    assert symbols[0]["file_path"] == "example.js"


def test_includes_javascript_line_number():

    source_code = """
class User {
}
"""

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.js"
    )

    assert symbols[0]["line"] == 2


def test_handles_empty_javascript_source():

    extractor = JavaScriptSymbolExtractor()

    symbols = extractor.extract_symbols(
        "",
        "empty.js"
    )

    assert symbols == []


def test_can_parse_100_javascript_files():

    extractor = JavaScriptSymbolExtractor()

    total_symbols = 0

    for i in range(100):

        source_code = f"""
class User{i} {{
    greet() {{
        console.log("Hello");
    }}
}}

function calculate{i}() {{
    return {i};
}}
"""

        symbols = extractor.extract_symbols(
            source_code,
            f"example{i}.js"
        )

        total_symbols += len(symbols)

    assert total_symbols >= 300