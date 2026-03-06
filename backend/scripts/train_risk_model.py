#!/usr/bin/env python3
"""
Train a supervised risk classification model (Gradient Boosting, Logistic Regression, or Random Forest)
for supply chain disruption probability. Uses data.csv (order-level) to build features aligned with
tools/risk_tools.py so the model can be used in get_disruption_probability().

Labels: 3-class from Disruption_Severity — Low (0)=None, Medium (1)=Low, High (2)=Medium or High.
Features: financial_health_risk, delivery_delay_frequency, region_instability, logistics_congestion,
          weather_disruption_prob, single_source, spend_pct (same order as risk_tools inference).

Output: data/risk_model.joblib, data/risk_model_features.json
"""

import csv
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_CSV = PROJECT_ROOT / "data.csv"
if not DATA_CSV.exists():
    DATA_CSV = DATA_DIR / "data.csv"

FEATURE_ORDER = [
    "financial_health_risk",
    "delivery_delay_frequency",
    "region_instability",
    "logistics_congestion",
    "weather_disruption_prob",
    "single_source",
    "spend_pct",
]


def _logistics_from_mode(mode: str) -> float:
    if mode == "Sea":
        return 0.7
    if mode == "Rail":
        return 0.4
    if mode == "Road":
        return 0.2
    return 0.1


def _severity_to_class(severity: str) -> int:
    if severity == "None" or severity is None or str(severity).strip() == "":
        return 0  # Low
    s = str(severity).strip()
    if s == "Low":
        return 1  # Medium
    if s in ("Medium", "High"):
        return 2  # High
    return 1


def load_and_prepare(csv_path: Path):
    import numpy as np

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for col in ["Supplier_Reliability_Score", "Historical_Disruption_Count", "Shipping_Mode", "Disruption_Severity"]:
            if col not in reader.fieldnames:
                raise ValueError(f"data.csv missing column: {col}")
        for row in reader:
            try:
                rel = float(row["Supplier_Reliability_Score"])
                hist = float(row["Historical_Disruption_Count"])
            except (ValueError, TypeError):
                continue
            financial_health_risk = 1.0 - max(0, min(1, rel))
            delivery_delay_frequency = min(1.0, hist / 20.0)
            region_instability = 0.0
            logistics_congestion = _logistics_from_mode(str(row.get("Shipping_Mode", "")))
            weather_disruption_prob = 0.0
            single_source = 0.0
            spend_pct = 0.0
            label = _severity_to_class(row.get("Disruption_Severity"))
            rows.append([
                financial_health_risk,
                delivery_delay_frequency,
                region_instability,
                logistics_congestion,
                weather_disruption_prob,
                single_source,
                spend_pct,
                label,
            ])
    arr = np.array(rows)
    X = arr[:, :-1].astype(np.float64)
    y = arr[:, -1].astype(np.intp)
    return X, y


def train_and_save(
    csv_path: Path,
    out_dir: Path,
    model_type: str = "random_forest",
):
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    import joblib

    X, y = load_and_prepare(csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    if model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    elif model_type == "gradient_boosting":
        model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    elif model_type == "logistic":
        model = LogisticRegression(max_iter=1000, random_state=42)
    else:
        raise ValueError("model_type must be random_forest, gradient_boosting, or logistic")

    model.fit(X, y)
    score = cross_val_score(model, X, y, cv=5, scoring="accuracy")
    print(f"Model: {model_type}, 5-fold CV accuracy: {score.mean():.3f} (+/- {score.std():.3f})")

    model_path = out_dir / "risk_model.joblib"
    joblib.dump(model, model_path)
    meta = {
        "feature_order": FEATURE_ORDER,
        "model_type": model_type,
        "classes": ["Low", "Medium", "High"],
        "n_samples": int(len(X)),
    }
    meta_path = out_dir / "risk_model_features.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved {model_path} and {meta_path}")
    return model, meta


def main():
    parser = argparse.ArgumentParser(description="Train risk classification model from data.csv")
    parser.add_argument("--csv", type=Path, default=DATA_CSV, help="Path to data.csv")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR, help="Output directory for model and meta")
    parser.add_argument("--model", choices=["random_forest", "gradient_boosting", "logistic"], default="random_forest")
    args = parser.parse_args()
    if not args.csv.exists():
        print(f"Error: {args.csv} not found")
        return 1
    train_and_save(args.csv, args.out_dir, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
