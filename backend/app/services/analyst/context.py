from app.models import Rfx

from ..comparison import price_rankings


def format_analyst_context(rfx: Rfx, comparison: dict, questionnaire: dict) -> str:
    lines = [
        f"RFx: {rfx.title}",
        f"Category: {rfx.category}",
        f"Buyer's own stated terms - payment: {rfx.payment_terms or 'not specified'} | "
        f"delivery: {rfx.delivery_terms or 'not specified'} | "
        f"quote validity requested: {rfx.validity_days or 'not specified'} days | "
        f"canonical currency: {rfx.canonical_currency}",
        "",
        "VENDOR ID REFERENCE (use these exact integer IDs in proposed_award.vendor_id - never guess "
        "or invent one):",
    ]
    for v in comparison["vendors"]:
        lines.append(f"  vendor_id={v['vendor_id']}: {v['name']}")

    lines.append(
        "\nPER-LINE-ITEM PRICE RANKINGS (cheapest first - use these numbers directly, do not "
        "re-derive or re-compare prices yourself; a vendor absent from a line's list did not quote it):"
    )
    for entry in price_rankings(comparison):
        lines.append(f"\n- {entry['sku_code']}: {entry['description']} (qty {entry['quantity']} {entry['unit']})")
        if not entry["ranked_vendors"]:
            lines.append("  No vendor quoted this line.")
        for i, v in enumerate(entry["ranked_vendors"], start=1):
            flag = ""
            if v["needs_review"]:
                flag = " [FLAGGED FOR REVIEW"
                flag += f" - evaluator: {v['evaluator_verdict']}]" if v["evaluator_verdict"] else "]"
            lead = f", lead time {v['lead_time_days']} days" if v["lead_time_days"] is not None else ""
            lines.append(
                f"  {i}. {v['vendor_name']} (vendor_id={v['vendor_id']}) - "
                f"{v['unit_price_normalized']} {rfx.canonical_currency}/unit{lead}{flag}"
            )

    lines.append("\nVENDOR QUESTIONNAIRE ANSWERS (the buyer defines what \"compliant\" means in their own "
                  "question - check the actual answers below against whatever bar they state):")
    for vendor in questionnaire["vendors"]:
        lines.append(f"\n{vendor['name']}:")
        for a in vendor["answers"]:
            if a["answer_text"] is None:
                lines.append(f"  Q{a['question_no']}. {a['question_text']} -> NOT ANSWERED")
            else:
                flag = f" [evaluator: {a['evaluator_verdict']}]" if a.get("evaluator_verdict") not in (None, "CONFIRMED") else ""
                lines.append(f"  Q{a['question_no']}. {a['question_text']} -> {a['answer_text']}{flag}")

    return "\n".join(lines)
