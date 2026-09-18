# src/apex_gateway/config.py
import os
from pathlib import Path

# Resolve the root of the repository dynamically (3 directories up from this file)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# --- File Paths ---
# Export these so your classifier and filter modules can import them
ONNX_MODEL_PATH = REPO_ROOT / "models" / "model.int8.onnx"
# ONNX_MODEL_PATH = str(REPO_ROOT / "models" / "model.int8.onnx")
MODEL_PATH = str(ONNX_MODEL_PATH)
TOKENIZER_PATH = str(REPO_ROOT / "models")
SCANNERS_FILE = str(REPO_ROOT / "data" / "scanners-user-agents.data")
# satisfy the import in initial_request_filter.py:
SCANNER_SIGNATURES_PATH = SCANNERS_FILE


# --- Logging Paths ---
LOG_DIR = REPO_ROOT / "logs"
LOG_FILE = str(LOG_DIR / "apex_security.log")

# --- Gateway Settings ---
# Ensure this points to the internal IP of the Target Node PC hosting Ollama
OLLAMA_TARGET_URL = os.getenv("OLLAMA_TARGET_URL", "http://192.168.1.100:11434/api/generate")

# ML Threshold
ML_CONFIDENCE_THRESHOLD = 0.5

