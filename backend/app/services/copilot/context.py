from sqlmodel import Session, select

from app.models import Rfx, RfxLineItem, RfxStatus

# Maps each catalog category to a broad use-case tier, so the co-pilot can reason
# about "light e-commerce vs heavy industrial vs export quality" instead of only
# matching specs in isolation - two SKUs can be spec-adjacent but wrong for each
# other's use case (a 3-ply e-commerce mailer is not a substitute for an export
# carton just because the dimensions are close).
_TIER_BY_CATEGORY = {
    "fmcg_ecom_3ply": "light e-commerce",
    "fmcg_ecom_5ply": "light e-commerce",
    "doc_mailer": "light e-commerce",
    "small_parts_3ply": "light e-commerce",
    "flatpack_3ply": "light e-commerce",
    "printed_3ply": "light e-commerce",
    "plain_rsc_3ply": "general purpose",
    "specialty": "general purpose",
    "plain_rsc_5ply": "industrial / heavy supply chain",
    "heavy_5ply": "industrial / heavy supply chain",
    "fmcg_master_5ply": "industrial / heavy supply chain",
    "printed_5ply": "industrial / heavy supply chain",
    "flatpack_5ply": "industrial / heavy supply chain",
    "fmcg_master_7ply": "export quality",
}


def _tier_for(category: str, description: str) -> str:
    if "export" in description.lower() or "ect-48" in description.lower():
        return "export quality"
    return _TIER_BY_CATEGORY.get(category, "general purpose")


def format_tier_context(catalog_line_items: list[dict]) -> str:
    by_tier: dict[str, list[str]] = {}
    for li in catalog_line_items:
        tier = _tier_for(li["category"], li["description"])
        by_tier.setdefault(tier, []).append(li["sku_code"])

    lines = [
        "CATALOG SKUs GROUPED BY USE-CASE TIER (light e-commerce / general purpose / "
        "industrial-heavy supply chain / export quality):",
    ]
    for tier, skus in by_tier.items():
        lines.append(f"- {tier}: {', '.join(skus)}")
    return "\n".join(lines)


def format_ordering_context(session: Session, top_n: int = 8) -> str:
    """Which SKUs this buyer actually orders most, from real sent RFxs - not
    drafts, since a draft that was never sent isn't a real ordering pattern.
    This is what lets the co-pilot resolve "the usual" to real SKUs instead of
    asking the buyer to re-list everything or guessing from the catalog alone."""
    rows = session.exec(
        select(RfxLineItem.sku_code, RfxLineItem.description, RfxLineItem.rfx_id)
        .join(Rfx, Rfx.id == RfxLineItem.rfx_id)
        .where(Rfx.status != RfxStatus.DRAFT)
    ).all()

    stats: dict[str, dict] = {}
    for sku_code, description, rfx_id in rows:
        if sku_code.startswith("NEW-"):
            continue  # one-off manual/new-SKU codes are never reused across RFxs - no frequency signal
        entry = stats.setdefault(sku_code, {"description": description, "rfx_ids": set()})
        entry["rfx_ids"].add(rfx_id)

    ranked = sorted(stats.items(), key=lambda kv: len(kv[1]["rfx_ids"]), reverse=True)[:top_n]
    if not ranked:
        return ""

    lines = [
        "MOST FREQUENTLY ORDERED SKUs, ranked by number of past RFxs actually sent to "
        "vendors that included them (highest first):",
    ]
    for sku_code, info in ranked:
        count = len(info["rfx_ids"])
        lines.append(f"- {sku_code}: {info['description']} (sent in {count} past RFx{'es' if count != 1 else ''})")
    return "\n".join(lines)
