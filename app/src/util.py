"""
util.py — General utility functions.
"""

_ONES = [
    "", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _two_digit_words(n: int) -> str:
    """Convert 0–99 to words."""
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + ("-" + _ONES[ones] if ones else "")


def year_to_words(year_str: str) -> str:
    """Convert a 4-digit year string to its typical spoken word form.

    Examples:
        "1900" -> "nineteen hundred"
        "1905" -> "nineteen oh-five"
        "1976" -> "nineteen seventy-six"
        "2000" -> "two thousand"
        "2005" -> "two thousand five"
        "2010" -> "two thousand ten"
        "2024" -> "twenty twenty-four"
    """
    if not year_str.isdigit() or len(year_str) != 4:
        raise ValueError("Expected a 4-digit year string, e.g. '2024'")

    year = int(year_str)
    first_half  = year // 100  # e.g. 19, 20
    second_half = year % 100   # e.g. 76, 05

    # 2000–2019: "two thousand" / "two thousand five" / "two thousand ten"
    if 2000 <= year <= 2019:
        if second_half == 0:
            return "two thousand"
        return "two thousand " + _two_digit_words(second_half)

    # Round-number years: 1900, 1800, 2100, etc.
    if second_half == 0:
        return _two_digit_words(first_half) + " hundred"

    # X0X years: 1905 -> "nineteen oh-five"
    if second_half < 10:
        return _two_digit_words(first_half) + " oh-" + _ONES[second_half]

    # Standard case: 1976 -> "nineteen seventy-six", 2024 -> "twenty twenty-four"
    return _two_digit_words(first_half) + " " + _two_digit_words(second_half)
