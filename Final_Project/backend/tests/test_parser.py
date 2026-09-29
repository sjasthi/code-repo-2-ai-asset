from app.parser.python_symbols import PythonSymbolExtractor


def test_extract_python_symbols():

    source_code = """
class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print("Hello")


def calculate_total(a, b):
    return a + b
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    names = [symbol["name"] for symbol in symbols]

    assert "User" in names
    assert "__init__" in names
    assert "greet" in names
    assert "calculate_total" in names


def test_identifies_class():

    source_code = """
class User:
    pass
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    assert symbols[0]["type"] == "class"
    assert symbols[0]["name"] == "User"


def test_identifies_function():

    source_code = """
def calculate_total():
    pass
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    assert symbols[0]["type"] == "function"
    assert symbols[0]["name"] == "calculate_total"


def test_identifies_method():

    source_code = """
class User:
    def login(self):
        pass
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    method = symbols[1]

    assert method["type"] == "method"
    assert method["name"] == "login"


def test_identifies_variable():

    source_code = """
message = "Hello"
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    assert symbols[0]["type"] == "variable"
    assert symbols[0]["name"] == "message"


def test_includes_file_path():

    source_code = """
class User:
    pass
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.py"
    )

    assert symbols[0]["file_path"] == "example.py"


def test_includes_line_number():

    source_code = """
class User:
    pass
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "example.py"
    )

    assert symbols[0]["line"] == 2


def test_identifies_tuple_unpacking_variables():

    source_code = """
x, y = 1, 2
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    names = [symbol["name"] for symbol in symbols]

    assert "x" in names
    assert "y" in names


def test_identifies_augmented_assignment_variable():

    source_code = """
count = 0
count += 1
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    names = [symbol["name"] for symbol in symbols]

    assert names.count("count") == 2


def test_does_not_treat_attribute_target_as_variable():

    source_code = """
obj.attr = 1
"""

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    assert symbols == []


def test_handles_multibyte_characters_without_corrupting_names():

    source_code = '''
def show_menu():
    print("No tasks found! Your schedule is clear. 🎉")

def add_task():
    print("✅ Task added.")
'''

    extractor = PythonSymbolExtractor()

    symbols = extractor.extract_symbols(
        source_code,
        "sample.py"
    )

    names = [symbol["name"] for symbol in symbols]

    assert "show_menu" in names
    assert "add_task" in names