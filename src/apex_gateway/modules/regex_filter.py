# src/apex_gateway/modules/regex_filter.py

import re
import logging
from .signatures import MALICIOUS_PATTERNS

logger = logging.getLogger(__name__)

COMPILED_SIGNATURES = []
for pattern in MALICIOUS_PATTERNS:
    try:
        COMPILED_SIGNATURES.append(re.compile(pattern))
    except Exception as e:
        logger.error(f"Failed to compile regex pattern '{pattern}': {e}")
        continue

def scan_prompt(prompt_string: str) -> bool:
    """
    Evaluates the extracted JSON "prompt" string against the compiled signature database.
    """
    if not prompt_string:
        return False
        
    for pattern in COMPILED_SIGNATURES:
        if pattern.search(prompt_string):
            return True 
            
    return False

# Alias to prevent import errors if any other script calls scan_payload
scan_payload = scan_prompt