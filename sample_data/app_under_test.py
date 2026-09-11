def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)  # bug: crashes when numbers is empty


scores = []
print(calculate_average(scores))
