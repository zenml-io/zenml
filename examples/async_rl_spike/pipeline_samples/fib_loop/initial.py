from zenml import step, pipeline

@step
def next_fib(a: int, b: int) -> int:
    return a + b

@pipeline(dynamic=True)
def fibonacci_pipeline():
    # Start with the first two Fibonacci numbers
    prev1 = 1
    prev2 = 1
    
    # Use a loop to apply next_fib 5 times
    # First call: (1, 1) -> 2
    # Second: (1, 2) -> 3
    # Third: (2, 3) -> 5
    # Fourth: (3, 5) -> 8
    # Fifth: (5, 8) -> 13
    # So we need 5 iterations of next_fib
    
    result1 = next_fib(a=prev1, b=prev2)  # 2
    result2 = next_fib(a=prev2, b=result1)  # 3
    result3 = next_fib(a=result1, b=result2)  # 5
    result4 = next_fib(a=result2, b=result3)  # 8
    result5 = next_fib(a=result3, b=result4)  # 13
    
    # Return the 7th Fibonacci number (13)
    return result5

if __name__ == "__main__":
    fibonacci_pipeline()
