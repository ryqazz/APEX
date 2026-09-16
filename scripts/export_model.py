from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

model_id = "deepset/deberta-v3-base-injection"

print(f"Downloading and exporting '{model_id}' to ONNX format...")
print("This might take a minute or two...")

# The export=True flag tells it to convert the PyTorch model to ONNX on the fly
model = ORTModelForSequenceClassification.from_pretrained(model_id, export=True)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Save the converted model and tokenizer to the models directory.
model.save_pretrained(MODEL_DIR)
tokenizer.save_pretrained(MODEL_DIR)

print("Success! 'model.onnx' has been saved to your folder.")   