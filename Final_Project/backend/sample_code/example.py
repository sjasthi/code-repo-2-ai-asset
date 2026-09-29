class User:

    def __init__(self, name):
        self.name = name

    def greet(self):
        print("Hello", self.name)


class Calculator:

    def add(self, a, b):
        return a + b


def calculate_total(a, b):
    total = a + b
    return total


message = "Code Dependency Graph"

# TESTING FOR PARSE PYTHON:
"""
{
  "file_path": "example.py",
  "source_code": "class User:\n\n    def __init__(self, name):\n        self.name = name\n\n    def greet(self):\n        print(\"Hello\", self.name)\n\n\nclass Calculator:\n\n    def add(self, a, b):\n        return a + b\n\n\ndef calculate_total(a, b):\n    total = a + b\n    return total\n\n\nmessage = \"Code Dependency Graph\""
}
"""