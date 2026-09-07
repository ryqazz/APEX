# main.py
import time
import json
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import Shared Config
from config import OLLAMA_TARGET_URL, ML_CONFIDENCE_THRESHOLD

# Import Internal Modules
from modules.telemetry_logger import log_telemetry, get_current_time
from modules.strike_manager import strike_mgr
from modules.initial_request_filter import is_scanner
from modules.regex_filter import scan_prompt
from modules.ml_classifier import evaluate_semantics, ml_enabled

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="Apex Security Gateway")
app.state.limiter = limiter

async def auto_ban_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = request.client.host
    if not strike_mgr.is_banned(client_ip):
        strike_mgr.ban_ip(client_ip)
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - RATE LIMIT EXCEEDED (AUTO-BAN)", 0)
        print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Rate Limit Exceeded)")
    return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Too Many Requests"})

app.add_exception_handler(RateLimitExceeded, auto_ban_rate_limit_handler)

class PromptSchema(BaseModel):
    prompt: str = Field(..., min_length=1)

@app.middleware("http")
async def security_firewall_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    if strike_mgr.is_banned(client_ip):
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden"})

    if request.url.path == "/api/generate" and request.method != "POST":
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - UNAUTHORIZED METHOD", 0)
        return JSONResponse(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, content={"detail": "Method Not Allowed"})
        
    return await call_next(request)

@app.get("/admin/banned")
async def view_banned_ips():
    return strike_mgr.get_banned_summary()

@app.post("/api/generate")
@limiter.limit("60/minute")
async def apex_gateway(request: Request):
    start_time = time.time()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    test_label = request.headers.get("x-test-label", "None")
        
    # Phase 2: Initial Request Filter (Scanner Detection)
    if is_scanner(user_agent):
        strike_mgr.ban_ip(client_ip) 
        log_telemetry(client_ip, request.method, user_agent, "N/A", test_label, "BLOCKED - SCANNER DETECTED", 0)
        print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Scanner Detected)")
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        body_bytes = await request.body()
        payload_dict = json.loads(body_bytes.decode('utf-8'))
        payload = PromptSchema(**payload_dict)
        prompt = payload.prompt
    except Exception:
        log_telemetry(client_ip, request.method, user_agent, "MALFORMED_DATA", test_label, "BLOCKED - INVALID JSON", 0)
        raise HTTPException(status_code=422, detail="Unprocessable Entity")
        
    if len(prompt) > 2000:
        log_telemetry(client_ip, request.method, user_agent, prompt[:50]+"...", test_label, "BLOCKED - OVERSIZED_PAYLOAD", 0)
        raise HTTPException(status_code=413, detail="Payload Too Large")

    is_malicious, rule_triggered = False, ""
    
    # Phase 3: Hybrid Payload Detection
    if scan_prompt(prompt):
        is_malicious, rule_triggered = True, "STATIC_REGEX_MATCH"
    elif ml_enabled:
        confidence = evaluate_semantics(prompt)
        if confidence >= ML_CONFIDENCE_THRESHOLD:
            is_malicious, rule_triggered = True, f"SEMANTIC_ML_MATCH ({confidence:.2f})"
        
    if is_malicious:
        strikes = strike_mgr.add_strike(client_ip)
        latency = round((time.time() - start_time) * 1000, 2)
        
        print(f"[{get_current_time()}] THREAT: IP {client_ip} | Strike {strikes}/3")
        
        if strikes >= 3:
            strike_mgr.ban_ip(client_ip) 
            print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Max Strikes Reached)")
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, f"BLOCKED - AUTO-BAN ({rule_triggered})", latency)
            raise HTTPException(status_code=403, detail="Forbidden")
        else:
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, f"BLOCKED - WARNING {strikes}/3 ({rule_triggered})", latency)
            raise HTTPException(status_code=403, detail="Forbidden")

    payload_dict["stream"] = False

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OLLAMA_TARGET_URL, json=payload_dict, timeout=60.0)
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, "ALLOWED - INFERENCE SUCCESS", round((time.time() - start_time) * 1000, 2))
            return JSONResponse(status_code=response.status_code, content=response.json())
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Bad Gateway")