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