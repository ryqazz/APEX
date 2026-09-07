import time
import json
import logging
import re
import os
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import onnxruntime as ort
from transformers import AutoTokenizer
import numpy as np

# ==========================================
# 1. CONFIGURATION & LOGGING SETUP
# ==========================================
OLLAMA_TARGET_URL = "http://192.168.0.20:11434/api/generate"
ONNX_MODEL_PATH = "deberta_v3_small_prompt_injection.onnx"
TOKENIZER_NAME = "microsoft/deberta-v3-small"
ML_CONFIDENCE_THRESHOLD = 0.5  # Baseline calibration

logger = logging.getLogger("apex_telemetry")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("apex_security.log")
logger.addHandler(file_handler)

logger.propagate = False

def log_telemetry(ip, method, user_agent, payload, test_label, action, latency):
    log_entry = {
        "Timestamp": datetime.utcnow().isoformat() + "Z",
        "Origin IP Address": ip,
        "HTTP Method": method,
        "User-Agent String": user_agent,
        "Raw JSON Payload": payload,
        "Test Label Header": test_label,
        "Routing Action Taken": action,
        "Processing Latency (ms)": latency
    }
    logger.info(json.dumps(log_entry))

def get_current_time():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

def calculate_softmax(logits):
    e_x = np.exp(logits - np.max(logits))
    return e_x / e_x.sum(axis=-1, keepdims=True)

# ==========================================
# 2. STATE MANAGEMENT & RATE LIMITING
# ==========================================
ip_strikes = {}
BANNED_IPS = set()

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="Apex Security Gateway")
app.state.limiter = limiter

async def auto_ban_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = request.client.host
    # Only log a rate limit ban if they weren't ALREADY banned for something else!
    if client_ip not in BANNED_IPS:
        BANNED_IPS.add(client_ip)
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - RATE LIMIT EXCEEDED (AUTO-BAN)", 0)
        print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Rate Limit Exceeded)")
    return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Too Many Requests"})

app.add_exception_handler(RateLimitExceeded, auto_ban_rate_limit_handler)

class PromptSchema(BaseModel):
    prompt: str = Field(..., min_length=1)

# ==========================================
# 3. CLASSIFIER & MIDDLEWARE
# ==========================================
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

DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "scanners-user-agents.data")
SCANNER_REGEX = load_crs_signatures(DATA_FILE_PATH)

INJECTION_REGEX = re.compile(r"(ignore (all )?previous instructions|system prompt|bypass|dan|do anything now|override)", re.IGNORECASE)

ml_enabled = False
try:
... (100 lines left)