from zenml import step, pipeline

@step
def get_words() -> list[str]:
    return ['sky', 'try', 'zen']

@step
def has_vowel(word: str) -> bool:
    return any(vowel in word for vowel in 'aeiou')

@step
def any_true(results: list[bool]) -> bool:
    return any(results)

@step
def report_found(found: bool) -> str:
    if found:
        return 'found'
    return 'not found'

@pipeline(dynamic=True)
def my_pipeline():
    words = get_words()           # returns an artifact handle
    has_vowels = has_vowel.map(words)  # fan out: one per word
    any_vowel = any_true(has_vowels)  # check if any is True
    result = report_found(any_vowel.load())  # use value in control flow

if __name__ == "__main__":
    my_pipeline()
