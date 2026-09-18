# src/apex_gateway/main.py
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
from .config import OLLAMA_TARGET_URL, ML_CONFIDENCE_THRESHOLD

# Import Internal Modules
from .modules.telemetry_logger import log_telemetry, get_current_time
from .modules.strike_manager import strike_mgr
from .modules.initial_request_filter import is_scanner
from .modules.regex_filter import scan_prompt
from .modules.ml_classifier import evaluate_semantics, ml_enabled

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app = FastAPI(title="Apex Security Gateway")
app.state.limiter = limiter


# Defines an async function for autobanning IP addresses that exceed the rate limit
# returns 429 Too Many Requests and bans the IP
# uses imported log_telemetry function to log the event
async def auto_ban_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = request.client.host
    if not strike_mgr.is_banned(client_ip):
        strike_mgr.ban_ip(client_ip)
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - RATE LIMIT EXCEEDED (AUTO-BAN)", 0)
        print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Rate Limit Exceeded)")
    return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Too Many Requests"})

# exists on the global scope, runs previous function when slowapi raises the ratelimitexceeded error
app.add_exception_handler(RateLimitExceeded, auto_ban_rate_limit_handler)

# parses through prompts and strictly requires the prompt field as a string with minimum length of 1 character.
class PromptSchema(BaseModel):
    prompt: str = Field(..., min_length=1)


# middleware
# security_firewall_middleware checks for banned IPs and unauthorized methods before processing requests
# logs events and returns appropriate HTTP responses for blocked requests, or else, passes request to next middleware
@app.middleware("http")
async def security_firewall_middleware(request: Request, call_next):
    client_ip = request.client.host
    
    if strike_mgr.is_banned(client_ip):
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - BANNED IP ATTEMPT", 0)
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden: IP is permanently banned."})

    if request.url.path == "/api/generate" and request.method != "POST":
        log_telemetry(client_ip, request.method, request.headers.get("user-agent", ""), "N/A", request.headers.get("x-test-label", "None"), "BLOCKED - UNAUTHORIZED METHOD", 0)
        return JSONResponse(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, content={"detail": "Method Not Allowed"})
        
    return await call_next(request)


# as of now, can be accessed by attackers
# allows viewing of banned IPs and their strike counts
@app.get("/admin/banned")
async def view_banned_ips():
    return strike_mgr.get_banned_summary()


# valid IPs can access this endpoint to generate responses from Ollama's API
# times the request, checks for scanners, validates the prompt, applies regex and ML filters, logs telemetry, and returns the response or appropriate error
@app.post("/api/generate")
@limiter.limit("60/minute")
async def apex_gateway(request: Request):
    start_time = time.time()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    test_label = request.headers.get("x-test-label", "None")


    # Phase 2: Initial Request Filter (Scanner Detection)
    # extracts user_agent from request header and checks against list of known scanners.
    # Detected scanners are blocked and logged, and the request is terminated with a 403 Forbidden response.    
    if is_scanner(user_agent):
        strike_mgr.ban_ip(client_ip) 
        log_telemetry(client_ip, request.method, user_agent, "N/A", test_label, "BLOCKED - SCANNER DETECTED", 0)
        print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Scanner Detected)")
        raise HTTPException(status_code=403, detail="Forbidden: Unauthorized scanner detected.")

    # reads raw bytes and converts into utf-8 to turn into a dictionary
    # done to catch character encoding exploits by enforcing utf-8 decoding and strict JSON parsing
    # extracts the prompt from the dictionary and validates it against the PromptSchema
    try:
        body_bytes = await request.body()
        payload_dict = json.loads(body_bytes.decode('utf-8'))
        payload = PromptSchema(**payload_dict)
        prompt = payload.prompt
    except Exception:
        log_telemetry(client_ip, request.method, user_agent, "MALFORMED_DATA", test_label, "BLOCKED - INVALID JSON", 0)
        raise HTTPException(status_code=422, detail="Unprocessable Entity")


    # simple check to prevent oversized payloads    
    if len(prompt) > 2000:
        log_telemetry(client_ip, request.method, user_agent, prompt[:50]+"...", test_label, "BLOCKED - OVERSIZED_PAYLOAD", 0)
        raise HTTPException(status_code=413, detail="Payload Too Large")


    #initialize is_malicious and rule_triggered variables
    is_malicious, rule_triggered = False, ""


    # Phase 3: Hybrid Payload Detection
    # if condition triggers upon regex match
    # elif condition flags as malicious if ML confidence score exceeds threshold
    if scan_prompt(prompt):
        is_malicious, rule_triggered = True, "STATIC_REGEX_MATCH"
    elif ml_enabled:
        confidence = evaluate_semantics(prompt)
        if confidence >= ML_CONFIDENCE_THRESHOLD:
            is_malicious, rule_triggered = True, f"SEMANTIC_ML_MATCH ({confidence:.2f})"

    # adds strike to the IP if malicious, logs telemetry, and bans the IP if strikes exceed 3
    if is_malicious:
        strikes = strike_mgr.add_strike(client_ip)
        latency = round((time.time() - start_time) * 1000, 2)
        
        print(f"[{get_current_time()}] THREAT: IP {client_ip} | Strike {strikes}/3")
        
        if strikes >= 3:
            strike_mgr.ban_ip(client_ip) 
            print(f"[{get_current_time()}] ACTION: IP {client_ip} BANNED (Max Strikes Reached)")
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, f"BLOCKED - AUTO-BAN ({rule_triggered})", latency)
            # FIX: Clearly state it's a ban
            raise HTTPException(status_code=403, detail="Forbidden: Maximum strikes reached. IP is permanently banned.")
        else:
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, f"BLOCKED - WARNING {strikes}/3 ({rule_triggered})", latency)
            # FIX: Clearly state it's a warning
            raise HTTPException(status_code=403, detail=f"Forbidden: Malicious activity flagged. Warning {strikes}/3.")

    # suppresses streaming, instead returns full response in one go
    payload_dict["stream"] = False

    # forwards the request to Ollama's API if it passes all security checks, logs telemetry, and returns the response
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OLLAMA_TARGET_URL, json=payload_dict, timeout=60.0)
            log_telemetry(client_ip, request.method, user_agent, prompt, test_label, "ALLOWED - INFERENCE SUCCESS", round((time.time() - start_time) * 1000, 2))
            return JSONResponse(status_code=response.status_code, content=response.json())
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Bad Gateway")