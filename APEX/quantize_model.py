from pathlib import Path

from onnxruntime.quantization import QuantType, quantize_dynamic

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODEL = PROJECT_ROOT / "model.onnx"
QUANTIZED_MODEL = PROJECT_ROOT / "model.int8.onnx"

if not SOURCE_MODEL.exists():
    raise FileNotFoundError(f"Source model not found: {SOURCE_MODEL}")

print(f"Quantizing {SOURCE_MODEL} -> {QUANTIZED_MODEL}")
quantize_dynamic(
    model_input=str(SOURCE_MODEL),
    model_output=str(QUANTIZED_MODEL),
    weight_type=QuantType.QInt8,
    per_channel=True,
    reduce_range=True,
)
print(f"Created {QUANTIZED_MODEL} ({QUANTIZED_MODEL.stat().st_size:,} bytes)")
