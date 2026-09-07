# modules/initial_request_filter.py
import re
import os

def load_crs_signatures(file_path: str):
    signatures = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    signatures.append(re.escape(line))
    if not signatures:
        signatures = [r"sqlmap", r"nikto", r"nmap", r"gobuster", r"acunetix"]
    return re.compile("|".join(signatures), re.IGNORECASE)

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scanners-user-agents.data")
SCANNER_REGEX = load_crs_signatures(DATA_FILE_PATH)

def is_scanner(user_agent: str) -> bool:
    if user_agent and user_agent != "Missing/Empty":
        return bool(SCANNER_REGEX.search(user_agent))
    return False