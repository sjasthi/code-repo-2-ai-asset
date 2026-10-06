class User {
    constructor(name) {
        this.name = name;
    }

    greet() {
        console.log("Hello", this.name);
    }
}

class Calculator {
    add(a, b) {
        return a + b;
    }
}

function calculateTotal(a, b) {
    const total = a + b;
    return total;
}

const message = "Code Dependency Graph";

// TESTING FOR PARSE JS:
/*
{
  "file_path": "example.js",
  "source_code": "class User {\n    constructor(name) {\n        this.name = name;\n    }\n\n    greet() {\n        console.log(\"Hello\", this.name);\n    }\n}\n\nclass Calculator {\n    add(a, b) {\n        return a + b;\n    }\n}\n\nfunction calculateTotal(a, b) {\n    const total = a + b;\n    return total;\n}\n\nconst message = \"Code Dependency Graph\";"
}
*/