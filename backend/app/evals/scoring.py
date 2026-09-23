import json
from pathlib import Path

from app.config import get_settings

PRICE_TOLERANCE_PCT = 0.02
# Mirrors data/seed/build_seed_data.py's FX_USD_TO_INR - this is the harness's own oracle for
# recomputing the "true" normalized price of a USD vendor line, independent of what the pipeline
# under test claims to have used.
FX_USD_TO_INR = 83.50


def load_ground_truth() -> dict:
    path = Path(get_settings().seed_data_dir) / "vendors" / "ground_truth.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_line_items_by_sku() -> dict:
    path = Path(get_settings().seed_data_dir) / "line_items.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    return {li["sku_code"]: li for li in items}


def expected_normalized_price(vendor_slug: str, gt_line: dict) -> float:
    if vendor_slug == "vendor_c_globalcorrfab":
        price_usd = gt_line["list_unit_price"]
        if gt_line["discount_applies"]:
            price_usd *= 1 - gt_line["discount_percent"] / 100
        return round(price_usd * FX_USD_TO_INR, 2)
    if gt_line.get("unit") == "100 pieces":
        # ground truth stores the vendor's stated per-100 price verbatim, not the
        # per-box price a correct normalization should produce
        return round(gt_line["unit_price"] / 100, 2)
    return gt_line["unit_price"]


def _answers_match(expected: str, predicted: str | None) -> bool:
    if predicted is None:
        return False
    try:
        return abs(float(expected) - float(predicted)) < 0.5
    except (TypeError, ValueError):
        pass
    e = expected.strip().lower().replace("_", " ")
    p = predicted.strip().lower().replace("_", " ")
    return e in p or p in e


def _line_is_wrong(line: dict, gt_by_sku: dict, vendor_slug: str) -> bool:
    """Ground truth for whether a single predicted line is actually correct - used to score the
    evaluator's own precision/recall, not the worker directly."""
    sku = line.get("sku_code")
    if sku is None:
        return False  # scored separately via sku_match_accuracy/coverage_precision
    gt_line = gt_by_sku.get(sku)
    if gt_line is None:
        return True  # matched to a SKU this vendor never actually quoted
    expected_price = expected_normalized_price(vendor_slug, gt_line)
    predicted_price = line.get("unit_price_normalized")
    if predicted_price is None or not expected_price:
        return True
    return abs(predicted_price - expected_price) / expected_price > PRICE_TOLERANCE_PCT


def score_vendor(vendor_slug: str, pipeline_output: dict, ground_truth: dict, line_items_by_sku: dict) -> dict:
    gt = ground_truth[vendor_slug]
    gt_by_sku = {line["sku_code"]: line for line in gt["lines"]}
    all_skus = set(line_items_by_sku.keys())
    expected_quoted = set(gt_by_sku.keys())
    expected_not_quoted = all_skus - expected_quoted

    predicted_by_sku = {}
    for line in pipeline_output["lines"]:
        if line.get("sku_code"):
            predicted_by_sku[line["sku_code"]] = line

    correct_matches, price_hits, priced_total = 0, 0, 0
    missed_lines, price_misses = [], []
    for sku in expected_quoted:
        pred = predicted_by_sku.get(sku)
        if pred is None:
            missed_lines.append(sku)
            continue
        correct_matches += 1
        expected_price = expected_normalized_price(vendor_slug, gt_by_sku[sku])
        predicted_price = pred.get("unit_price_normalized")
        priced_total += 1
        if predicted_price is not None and expected_price and abs(predicted_price - expected_price) / expected_price <= PRICE_TOLERANCE_PCT:
            price_hits += 1
        else:
            price_misses.append({"sku": sku, "expected": expected_price, "predicted": predicted_price})

    over_claimed = [sku for sku in expected_not_quoted if sku in predicted_by_sku]

    gt_answers = gt["answers"]
    pred_answers = {str(a["question_no"]): a for a in pipeline_output["answers"]}
    answer_hits = sum(
        1 for q_no, expected in gt_answers.items()
        if q_no in pred_answers and _answers_match(expected, pred_answers[q_no].get("answer_text"))
    )
    all_question_nos = {str(i) for i in range(1, 9)}
    blanks_correctly_left_blank = sum(
        1 for q_no in (all_question_nos - set(gt_answers)) if q_no not in pred_answers
    )
    blanks_filled_anyway = [
        q_no for q_no in (all_question_nos - set(gt_answers)) if q_no in pred_answers
    ]

    return {
        "vendor_slug": vendor_slug,
        "sku_match_accuracy": round(correct_matches / len(expected_quoted), 3) if expected_quoted else 1.0,
        "price_accuracy": round(price_hits / priced_total, 3) if priced_total else 1.0,
        "coverage_precision": round(1 - len(over_claimed) / len(expected_not_quoted), 3) if expected_not_quoted else 1.0,
        "questionnaire_accuracy": round(answer_hits / len(gt_answers), 3) if gt_answers else 1.0,
        "blanks_handled_correctly": blanks_correctly_left_blank,
        "blanks_total": len(all_question_nos - set(gt_answers)),
        "missed_lines": missed_lines,
        "over_claimed_lines": over_claimed,
        "price_misses": price_misses,
        "blanks_filled_anyway": blanks_filled_anyway,
    }


def score_evaluator(pipeline_output: dict, ground_truth: dict, vendor_slug: str) -> dict:
    gt = ground_truth[vendor_slug]
    gt_by_sku = {line["sku_code"]: line for line in gt["lines"]}
    tp = fp = fn = tn = 0
    for line in pipeline_output["lines"]:
        disputed = line["evaluator_verdict"] == "DISPUTED"
        wrong = _line_is_wrong(line, gt_by_sku, vendor_slug)
        if disputed and wrong:
            tp += 1
        elif disputed and not wrong:
            fp += 1
        elif not disputed and wrong:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn, "tn": tn}
