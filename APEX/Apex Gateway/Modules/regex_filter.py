# modules/regex_filter.py
import re

INJECTION_REGEX = re.compile(
    r"(ignore (all )?previous instructions|system prompt|bypass|dan|do anything now|override)", 
    re.IGNORECASE
)

def scan_prompt(prompt: str) -> bool:
    return bool(INJECTION_REGEX.search(prompt))