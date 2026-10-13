import pytest

from app.parser.tags_symbols import TagsSymbolExtractor
from app.parser.registry import detect_language


def extract(language, source_code):
    extractor = TagsSymbolExtractor(language)

    symbols = extractor.extract_symbols(source_code, "sample")

    return {
        (symbol["type"], symbol["name"])
        for symbol in symbols
    }


def test_extract_go_symbols():

    symbols = extract("go", """
package main

type User struct { Name string }

type Greeter interface { Greet() }

func (u User) Greet() {}

func main() {}
""")

    assert ("class", "User") in symbols
    assert ("interface", "Greeter") in symbols
    assert ("method", "Greet") in symbols
    assert ("function", "main") in symbols


def test_extract_rust_symbols():

    symbols = extract("rust", """
struct User { name: String }

trait Greet {}

impl User {
    fn new() -> Self { todo!() }
}

fn main() {}

mod util {}
""")

    assert ("class", "User") in symbols
    assert ("interface", "Greet") in symbols
    assert ("module", "util") in symbols
    assert ("function", "main") in symbols


def test_rust_impl_function_is_only_reported_as_method():

    symbols = extract("rust", """
impl User {
    fn new() -> Self { todo!() }
}
""")

    assert ("method", "new") in symbols
    assert ("function", "new") not in symbols


def test_extract_java_symbols():

    symbols = extract("java", """
public class User {
    public User() {}

    void greet() {}
}

interface Greeter {}
""")

    assert ("class", "User") in symbols
    assert ("method", "User") in symbols
    assert ("method", "greet") in symbols
    assert ("interface", "Greeter") in symbols


def test_extract_c_symbols():

    symbols = extract("c", """
struct User { int id; };

typedef int UserId;

int add(int a, int b) { return a + b; }
""")

    assert ("class", "User") in symbols
    assert ("type", "UserId") in symbols
    assert ("function", "add") in symbols


def test_extract_cpp_symbols():

    symbols = extract("cpp", """
class User {
public:
    void greet() {}
};

struct Point { int x; };

void User::save() {}

int main() { return 0; }
""")

    assert ("class", "User") in symbols
    assert ("class", "Point") in symbols
    assert ("method", "greet") in symbols
    assert ("method", "save") in symbols
    assert ("function", "main") in symbols


def test_extract_ruby_symbols():

    symbols = extract("ruby", """
module Admin
  class User < Base
    def greet; end

    def self.find; end
  end
end
""")

    assert ("module", "Admin") in symbols
    assert ("class", "User") in symbols
    assert ("method", "greet") in symbols
    assert ("method", "find") in symbols


def test_symbols_include_file_path_and_line():

    extractor = TagsSymbolExtractor("go")

    symbols = extractor.extract_symbols(
        "package main\n\nfunc main() {}\n",
        "main.go"
    )

    assert symbols == [{
        "type": "function",
        "name": "main",
        "file_path": "main.go",
        "line": 3
    }]


def test_empty_source_returns_no_symbols():

    assert extract("rust", "") == set()


@pytest.mark.parametrize("file_path, language", [
    ("main.go", "go"),
    ("lib.rs", "rust"),
    ("User.java", "java"),
    ("util.c", "c"),
    ("util.h", "c"),
    ("app.cpp", "cpp"),
    ("app.hpp", "cpp"),
    ("user.rb", "ruby"),
])
def test_detect_language_from_extension(file_path, language):

    assert detect_language(file_path) == language


def test_detect_language_accepts_aliases():

    assert detect_language("x", "golang") == "go"
    assert detect_language("x", "C++") == "cpp"
