"""Script to generate and sum 10 random numbers."""

import random


def sum_random_numbers() -> int:
    """Generate 10 random numbers between 1-100 and return their sum.

    Returns:
        The sum of 10 randomly generated numbers.
    """
    numbers = []
    for _ in range(10):  # Use _ for unused loop variable
        # Using standard random for demo purposes (not cryptographically secure)
        num = random.randint(1, 100)  # noqa: S311
        numbers.append(num)

    total = sum(numbers)
    print(f"Random numbers: {numbers}")
    print(f"Sum: {total}")
    return total


if __name__ == "__main__":
    sum_random_numbers()
