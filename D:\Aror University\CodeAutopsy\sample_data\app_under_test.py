def calculate_average(numbers):
    """Return the average of a list of numbers.

    If the list is empty, returns 0 to avoid a ZeroDivisionError.
    """
    if not numbers:
        return 0
    total = sum(numbers)
    return total / len(numbers)

# Example usage
scores = [10, 20, 30, 40, 50]  # replace with actual scores list
print(calculate_average(scores))
