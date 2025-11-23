"""
Validation logic for requirement answers.

Validates user answers against expected formats.
Follows SRP: Answer validation only.
"""

from typing import Any, Dict, List, Tuple
import re


def validate_text(answer: str) -> Tuple[bool, str]:
    """Validate text answer"""
    if not answer or not answer.strip():
        return False, "Answer cannot be empty"

    if len(answer.strip()) < 10:
        return False, "Answer too short (minimum 10 characters)"

    return True, ""


def validate_list(answer: str) -> Tuple[bool, str]:
    """Validate comma-separated list"""
    if not answer or not answer.strip():
        return False, "List cannot be empty"

    items = [item.strip() for item in answer.split(',')]
    items = [item for item in items if item]  # Remove empty

    if len(items) == 0:
        return False, "No valid items in list"

    return True, ""


def validate_dict(answer: str) -> Tuple[bool, str]:
    """
    Validate dictionary format: key: val1, val2; key2: val3, val4
    """
    if not answer or not answer.strip():
        return False, "Dictionary cannot be empty"

    # Split by semicolon or newline for multiple entries
    entries = re.split(r'[;\n]', answer)
    entries = [e.strip() for e in entries if e.strip()]

    if len(entries) == 0:
        return False, "No valid entries in dictionary"

    # Validate each entry has key:value format
    for entry in entries:
        if ':' not in entry:
            return False, f"Invalid format in '{entry}'. Expected 'key: value'"

    return True, ""


def validate_optional(answer: str) -> Tuple[bool, str]:
    """Validate optional answer (always valid)"""
    return True, ""


def validate_answer(
    answer: str,
    question_type: str
) -> Tuple[bool, str]:
    """
    Validate answer based on question type.

    Returns: (is_valid, error_message)
    """
    validators = {
        "text": validate_text,
        "list": validate_list,
        "dict": validate_dict,
        "optional": validate_optional
    }

    validator = validators.get(question_type)
    if not validator:
        return False, f"Unknown question type: {question_type}"

    return validator(answer)


def parse_list_answer(answer: str) -> List[str]:
    """Parse comma-separated list answer"""
    items = [item.strip() for item in answer.split(',')]
    return [item for item in items if item]


def parse_dict_answer(answer: str) -> Dict[str, List[str]]:
    """
    Parse dictionary answer.

    Format: lib1: feat1, feat2; lib2: feat3, feat4
    """
    result = {}

    # Split by semicolon or newline
    entries = re.split(r'[;\n]', answer)

    for entry in entries:
        entry = entry.strip()
        if not entry or ':' not in entry:
            continue

        key, value = entry.split(':', 1)
        key = key.strip()
        values = [v.strip() for v in value.split(',')]
        values = [v for v in values if v]

        if key and values:
            result[key] = values

    return result


def parse_answer(answer: str, question_type: str) -> Any:
    """Parse answer based on question type"""
    parsers = {
        "text": lambda a: a.strip(),
        "list": parse_list_answer,
        "dict": parse_dict_answer,
        "optional": lambda a: [u.strip() for u in a.split()] if a.strip() else None
    }

    parser = parsers.get(question_type, lambda a: a)
    return parser(answer)
