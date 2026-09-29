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