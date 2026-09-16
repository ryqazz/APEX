import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"

OLLAMA_TARGET_URL = os.getenv(
	"OLLAMA_TARGET_URL",
	"http://127.0.0.1:11434/api/generate",
)
ONNX_MODEL_PATH = MODEL_DIR / "model.int8.onnx"
TOKENIZER_PATH = MODEL_DIR
SCANNER_SIGNATURES_PATH = DATA_DIR / "scanners-user-agents.data"
LOG_PATH = LOG_DIR / "apex_security.log"
ML_CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.5"))
ML_CONFIDENCE_THRESHOLD = 0.5