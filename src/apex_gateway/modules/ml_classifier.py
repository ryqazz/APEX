import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from datasets import load_dataset
from scipy.special import softmax
import os
from pathlib import Path
from ..config import ONNX_MODEL_PATH, TOKENIZER_PATH

QUANTIZED_MODEL_PATH = ONNX_MODEL_PATH
ORIGINAL_MODEL_PATH = ONNX_MODEL_PATH.with_name("model.onnx")
if not ONNX_MODEL_PATH.exists() and ORIGINAL_MODEL_PATH.exists():
    ONNX_MODEL_PATH = ORIGINAL_MODEL_PATH

_session = None
_tokenizer = None
ml_enabled = ONNX_MODEL_PATH.exists()


def evaluate_semantics(prompt: str) -> float:
    global _session, _tokenizer

    if not ml_enabled:
        return 0.0

    if _session is None:
        _session = ort.InferenceSession(str(ONNX_MODEL_PATH))
        _tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH, local_files_only=True)

    inputs = _tokenizer(prompt, return_tensors="np", padding=True, truncation=True, max_length=512)
    ort_inputs = {
        "input_ids": inputs["input_ids"].astype(np.int64),
        "attention_mask": inputs["attention_mask"].astype(np.int64),
    }
    logits = _session.run(None, ort_inputs)[0][0]
    return float(softmax(logits)[1])

def load_hf_datasets():
    print("Loading HuggingFace datasets...")
    try:
        deepset_ds = load_dataset("deepset/prompt-injections", split="train")
        hackaprompt_ds = load_dataset("hackaprompt/hackaprompt-dataset", split="train")
        print(f"Success: Loaded {len(deepset_ds)} deepset records and {len(hackaprompt_ds)} HackAPrompt records.\n")
    except Exception as e:
        print(f"Warning: Could not fetch datasets. Error: {e}\n")

def run_classifier_test():
    # 1. Initialize ONNX and Tokenizer
    # Make sure your actual .onnx file matches this name and is in the APEX/APEX folder
    print(f"Initializing local ONNX session using '{ONNX_MODEL_PATH}'...")
    if not os.path.exists(ONNX_MODEL_PATH):
        print(f"ERROR: '{ONNX_MODEL_PATH}' not found in the current directory.")
        print("Please place your ONNX model file in the APEX/APEX folder before running.")
        return

    session = ort.InferenceSession(ONNX_MODEL_PATH)
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH, local_files_only=True)
    print("ONNX runtime initialized successfully.\n")

    # 2. Terminal Loop for Manual Testing
    print("="*55)
    print("Semantic ML Classifier - Local Terminal Test")
    print("Threshold: 0.5 (Scores >= 0.5 flagged as injection)")
    print("Type 'exit' to quit.")
    print("="*55)

    while True:
        user_input = input("\n[Terminal] Enter text string: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input.strip():
            continue

        # Tokenize input
        inputs = tokenizer(user_input, return_tensors="np", padding=True, truncation=True, max_length=512)
        
        # Prepare inputs for ONNX
        ort_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64)
        }
        
        # Run inference
        outputs = session.run(None, ort_inputs)
        logits = outputs[0][0]
        
        # Apply softmax to get confidence score
        probabilities = softmax(logits)
        confidence_score = probabilities[1] # Index 1 is typically the 'injection' class
        
        # Check against 0.5 baseline
        is_injection = confidence_score >= 0.5
        
        print(f"--> Classification: {'[INJECTION DETECTED]' if is_injection else '[SAFE]'}")
        print(f"--> Confidence Score: {confidence_score:.4f} (Baseline: 0.5)")

if __name__ == "__main__":
    load_hf_datasets()
    run_classifier_test()