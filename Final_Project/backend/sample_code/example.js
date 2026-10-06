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