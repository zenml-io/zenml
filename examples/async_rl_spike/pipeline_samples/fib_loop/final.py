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
    result = prev1
    for _ in range(5):
        result = next_fib(a=prev2, b=prev1).load()
        prev1 = prev2
        prev2 = result

if __name__ == "__main__":
    fibonacci_pipeline()
