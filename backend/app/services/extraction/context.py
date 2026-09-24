import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


def _load_json(name: str):
    path = Path(get_settings().seed_data_dir) / name
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def load_reference_bundle(line_items_file: str = "line_items.json") -> dict:
    """`line_items_file` defaults to the seeded demo RFx's own 30 line items,
    used by the extraction pipeline to match against what vendors were actually
    sent. The co-pilot passes "sku_catalog.json" instead - the buyer's broader
    SKU catalog, independent of any single RFx - so it can ground drafts
    against items that were never part of that one demo RFx."""
    return {
        "rfx": _load_json("rfx.json"),
        "line_items": _load_json(line_items_file),
        "questionnaire": _load_json("questionnaire.json"),
    }


def format_reference_context(bundle: dict) -> str:
    rfx = bundle["rfx"]
    lines = [
        f"Buyer: {rfx['buyer_name']} | RFx: {rfx['title']}",
        f"Canonical currency: {rfx['canonical_currency']} | "
        f"buyer's requested payment terms: {rfx['payment_terms']} | "
        f"delivery terms: {rfx['delivery_terms']} | quote validity requested: {rfx['validity_days']} days",
        f"Reference FX rates (use these, do not estimate): "
        + ", ".join(f"1 {pair.split('_')[0]} = {rate} {pair.split('_')[1]}" for pair, rate in rfx["fx_rates"].items()),
        "",
        "CANONICAL LINE ITEMS (match every vendor line against this list by spec - ply, flute, "
        "dimensions, GSM, printed - never assume the vendor's own code or row order lines up with this list):",
    ]
    for li in bundle["line_items"]:
        spec = li["spec_attributes"]
        bf_part = f" min_bf={spec['min_bf']}" if spec.get("min_bf") is not None else ""
        lines.append(
            f"- {li['sku_code']}: {li['description']} | requested qty {li['quantity']} {li['unit']} | "
            f"spec: ply={spec['ply']} flute={spec['flute']} dims={spec['dimensions_mm']}mm gsm={spec['gsm']} "
            f"printed={spec['printed']} weight={spec['weight_kg']}kg{bf_part} | "
            f"last known price: {li['reference_unit_price']} {li['reference_currency']}/{li['unit']} "
            f"({li['reference_period_label']}) - use this if the vendor says something like "
            f"'same as last year' for this item"
        )
    lines.append("")
    lines.append("QUALITY QUESTIONNAIRE (question_no, type, text):")
    for q in bundle["questionnaire"]:
        lines.append(f"- Q{q['question_no']} ({q['question_type']}): {q['question_text']}")
    return "\n".join(lines)
