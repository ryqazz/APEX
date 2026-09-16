import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from datasets import load_dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from apex_gateway.config import ML_CONFIDENCE_THRESHOLD
from apex_gateway.modules.ml_classifier import evaluate_semantics


def evaluate(samples, threshold):
    counts = Counter()
    scores = []

    for text, expected in samples:
        score = evaluate_semantics(text)
        predicted = int(score >= threshold)
        counts[(expected, predicted)] += 1
        scores.append((score, expected))

    true_positive = counts[(1, 1)]
    true_negative = counts[(0, 0)]
    false_positive = counts[(0, 1)]
    false_negative = counts[(1, 0)]
    total = len(samples)

    accuracy = (true_positive + true_negative) / total if total else 0.0
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = false_positive / (false_positive + true_negative) if false_positive + true_negative else 0.0

    return {
        "threshold": threshold,
        "samples": total,
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "score_range": [round(min(score for score, _ in scores), 4), round(max(score for score, _ in scores), 4)] if scores else [0.0, 0.0],
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate the APEX semantic prompt-injection classifier.")
    parser.add_argument("--hack-limit", type=int, default=250, help="Number of HackAPrompt attack samples to include.")
    parser.add_argument("--threshold", type=float, default=ML_CONFIDENCE_THRESHOLD)
    args = parser.parse_args()

    deepset = load_dataset("deepset/prompt-injections", split="train")
    samples = [(row["text"], int(row["label"])) for row in deepset]

    hackaprompt = load_dataset("hackaprompt/hackaprompt-dataset", split="train")
    for row in hackaprompt.select(range(min(args.hack_limit, len(hackaprompt)))):
        samples.append((row["prompt"], 1))

    report = evaluate(samples, args.threshold)
    report["datasets"] = {
        "deepset_prompt_injections": len(deepset),
        "hackaprompt_attack_samples": min(args.hack_limit, len(hackaprompt)),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
