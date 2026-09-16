# modules/telemetry_logger.py
import json
import logging
from datetime import datetime
from ..config import LOG_PATH

logger = logging.getLogger("apex_telemetry")
logger.setLevel(logging.INFO)

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(LOG_PATH)
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