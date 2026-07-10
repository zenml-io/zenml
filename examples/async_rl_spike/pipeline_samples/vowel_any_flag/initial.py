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
    words = get_words()
    has_vowels = has_vowel.map(words)
    any_vowel = any_true(results=has_vowels)
    result = report_found(found=any_vowel)

if __name__ == "__main__":
    my_pipeline()
