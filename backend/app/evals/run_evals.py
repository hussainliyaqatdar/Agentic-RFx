"""Runs the extraction pipeline against all 5 fabricated vendors and scores the result
against data/seed/vendors/ground_truth.json. Makes real Gemini calls - requires
GEMINI_API_KEY in backend/.env.

    uv run python -m app.evals.run_evals
"""

import json
import statistics
import sys
from pathlib import Path

from app.services.extraction.pipeline import run_pipeline_for_vendor

from .scoring import load_ground_truth, load_line_items_by_sku, score_evaluator, score_vendor

VENDOR_SLUGS = [
    "vendor_a_apex",
    "vendor_b_shreeji",
    "vendor_c_globalcorrfab",
    "vendor_d_suretypack",
    "vendor_e_balaji",
]


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _print_vendor_report(slug: str, score: dict, evaluator_score: dict) -> None:
    print(f"\n=== {slug} ===")
    print(f"  SKU match accuracy:      {_fmt_pct(score['sku_match_accuracy'])}")
    print(f"  Price accuracy:          {_fmt_pct(score['price_accuracy'])}")
    print(f"  Coverage precision:      {_fmt_pct(score['coverage_precision'])}  (didn't claim gaps as quoted)")
    print(f"  Questionnaire accuracy:  {_fmt_pct(score['questionnaire_accuracy'])}")
    print(f"  Blanks left blank:       {score['blanks_handled_correctly']}/{score['blanks_total']}")
    print(f"  Evaluator precision/recall: {_fmt_pct(evaluator_score['precision'])} / {_fmt_pct(evaluator_score['recall'])}"
          f"  (tp={evaluator_score['tp']} fp={evaluator_score['fp']} fn={evaluator_score['fn']} tn={evaluator_score['tn']})")
    if score["missed_lines"]:
        print(f"  Missed lines (vendor quoted, pipeline didn't match): {score['missed_lines']}")
    if score["over_claimed_lines"]:
        print(f"  Over-claimed lines (pipeline matched, vendor didn't quote): {score['over_claimed_lines']}")
    if score["blanks_filled_anyway"]:
        print(f"  Filled a blank the vendor left unanswered: Q{score['blanks_filled_anyway']}")
    for miss in score["price_misses"]:
        print(f"  Price miss on {miss['sku']}: expected {miss['expected']}, got {miss['predicted']}")


def _print_aggregate(results: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("AGGREGATE ACROSS ALL 5 VENDORS")
    for key, label in [
        ("sku_match_accuracy", "SKU match accuracy"),
        ("price_accuracy", "Price accuracy"),
        ("coverage_precision", "Coverage precision"),
        ("questionnaire_accuracy", "Questionnaire accuracy"),
    ]:
        values = [r["score"][key] for r in results]
        print(f"  avg {label}: {statistics.mean(values):.0%}")
    precisions = [r["evaluator_score"]["precision"] for r in results if r["evaluator_score"]["precision"] is not None]
    recalls = [r["evaluator_score"]["recall"] for r in results if r["evaluator_score"]["recall"] is not None]
    if precisions:
        print(f"  avg evaluator precision: {statistics.mean(precisions):.0%}")
    if recalls:
        print(f"  avg evaluator recall: {statistics.mean(recalls):.0%}")


def main() -> None:
    ground_truth = load_ground_truth()
    line_items_by_sku = load_line_items_by_sku()
    results = []
    for slug in VENDOR_SLUGS:
        print(f"Running pipeline for {slug}...", file=sys.stderr)
        try:
            output = run_pipeline_for_vendor(slug)
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)
            continue
        score = score_vendor(slug, output, ground_truth, line_items_by_sku)
        evaluator_score = score_evaluator(output, ground_truth, slug)
        results.append({"vendor": slug, "score": score, "evaluator_score": evaluator_score, "output": output})
        _print_vendor_report(slug, score, evaluator_score)

    if results:
        _print_aggregate(results)

    out_path = Path("eval_results.json")
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results (including raw pipeline output) written to {out_path}")


if __name__ == "__main__":
    main()
