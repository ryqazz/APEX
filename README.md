# APEX

APEX is a defense-in-depth local LLM gateway for scanner detection, prompt-injection filtering, strike-based banning, and telemetry logging before requests reach Ollama.

## Project Layout

```text
src/apex_gateway/       FastAPI gateway and security modules
scripts/                Model export, quantization, and evaluation tools
models/                 ONNX model and tokenizer assets
data/                   Scanner user-agent signatures
logs/                   Runtime telemetry output
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run The Gateway

Set the Ollama endpoint when it is not running locally:

```powershell
$env:OLLAMA_TARGET_URL = "http://127.0.0.1:11434/api/generate"
python -m uvicorn apex_gateway.main:app --app-dir src --host 0.0.0.0 --port 8000
```

## Evaluate The Classifier

```powershell
python scripts/evaluate_semantic_model.py --hack-limit 250
```

The evaluator reports accuracy, precision, recall, F1, confusion-matrix counts, and false-positive rate at the configured threshold.
