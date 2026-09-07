# modules/ml_classifier.py
import os
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from config import ONNX_MODEL_PATH, TOKENIZER_NAME

def calculate_softmax(logits):
    e_x = np.exp(logits - np.max(logits))
    return e_x / e_x.sum(axis=-1, keepdims=True)

ml_enabled = False
ort_session = None
tokenizer = None

try:
    if os.path.exists(ONNX_MODEL_PATH):
        ort_session = ort.InferenceSession(ONNX_MODEL_PATH)
        tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)
        ml_enabled = True
except Exception:
    pass

def evaluate_semantics(prompt: str) -> float:
    if not ml_enabled:
        return 0.0
    inputs = tokenizer(prompt, return_tensors="np", truncation=True, max_length=512)
    ort_inputs = {ort_session.get_inputs()[0].name: inputs["input_ids"]}
    logits = ort_session.run(None, ort_inputs)[0]
    confidence = calculate_softmax(logits)[0][1] if logits.shape[-1] > 1 else calculate_softmax(logits)[0][0]
    return float(confidence)