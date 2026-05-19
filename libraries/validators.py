"""Format-level validators."""
import re


def luhn_valid(digits: str) -> bool:
    """Standard Luhn checksum used for credit card numbers."""
    digits = re.sub(r"[\s-]", "", digits)
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0
