from dependency_helpers import greet, calculate_total


def main():
    message = greet("World")
    total = calculate_total(5, 10)

    print(message)
    print(total)


if __name__ == "__main__":
    main()