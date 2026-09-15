from optimum.onnxruntime import ORTModelForSequenceClassification
from transformers import AutoTokenizer

model_id = "deepset/deberta-v3-base-injection"

print(f"Downloading and exporting '{model_id}' to ONNX format...")
print("This might take a minute or two...")

# The export=True flag tells it to convert the PyTorch model to ONNX on the fly
model = ORTModelForSequenceClassification.from_pretrained(model_id, export=True)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Save the converted model and tokenizer directly to your current APEX directory
model.save_pretrained(".")
tokenizer.save_pretrained(".")

print("Success! 'model.onnx' has been saved to your folder.")   