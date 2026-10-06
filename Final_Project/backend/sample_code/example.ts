class User {
    name: string;

    constructor(name: string) {
        this.name = name;
    }

    greet(): void {
        console.log("Hello", this.name);
    }
}

function calculateTotal(a: number, b: number): number {
    const total = a + b;
    return total;
}

const message: string = "Code Dependency Graph";

// TESTING FOR PARSE TS:
/*
{
  "file_path": "example.ts",
  "source_code": "class User {\n    name: string;\n\n    constructor(name: string) {\n        this.name = name;\n    }\n\n    greet(): void {\n        console.log(\"Hello\", this.name);\n    }\n}\n\nfunction calculateTotal(a: number, b: number): number {\n    const total = a + b;\n    return total;\n}\n\nconst message: string = \"Code Dependency Graph\";"
}
*/