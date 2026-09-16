# src/apex_gateway/modules/telemetry_logger.py
import os
import json
import datetime
from ..config import LOG_DIR, LOG_FILE

# CRITICAL FIX: Ensure the logs directory exists before we try to open files in it
os.makedirs(LOG_DIR, exist_ok=True)

def get_current_time():
    """Returns the current formatted timestamp for console output."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_telemetry(client_ip, method, user_agent, payload, test_label, action, latency):
    """
    Appends structured JSON telemetry data to the local log file.
    """
    log_entry = {
        "timestamp": get_current_time(),
        "client_ip": client_ip,
        "method": method,
        "user_agent": user_agent,
        "payload": payload,
        "x_test_label": test_label,
        "action": action,
        "latency_ms": latency
    }
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"[{get_current_time()}] ERROR: Failed to write telemetry to log file: {e}")