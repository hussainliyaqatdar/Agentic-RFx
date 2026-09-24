"""Tracks real token usage and spend across Gemini calls within this process, and
refuses to make further calls once a session budget is exceeded. This exists
because billing is real money, not a quota to shrug off - every call's actual
cost (from the API's own usage_metadata, not an estimate) is logged as it happens.
"""

# Pricing for gemini-3.1-flash-lite (per ai.google.dev/gemini-api/docs/pricing).
# Update these together with GEMINI_MODEL in .env - they're specific to that
# model, not a general Gemini rate.
PRICE_PER_M_INPUT_USD = 0.25
PRICE_PER_M_OUTPUT_USD = 1.50

SESSION_BUDGET_USD = 1.00

_usage_log: list[dict] = []


class BudgetExceededError(RuntimeError):
    pass


def total_spent_usd() -> float:
    return sum(entry["cost_usd"] for entry in _usage_log)


def check_budget_before_call() -> None:
    spent = total_spent_usd()
    if spent >= SESSION_BUDGET_USD:
        raise BudgetExceededError(
            f"Session spend ${spent:.4f} has reached the ${SESSION_BUDGET_USD:.2f} budget cap - "
            "refusing to make another Gemini call. Call cost_tracker.raise_budget(...) to proceed."
        )


def raise_budget(new_budget_usd: float) -> None:
    global SESSION_BUDGET_USD
    SESSION_BUDGET_USD = new_budget_usd


def record_usage(response, label: str) -> dict:
    usage = getattr(response, "usage_metadata", None)
    input_tokens = getattr(usage, "prompt_token_count", None) or 0
    output_tokens = getattr(usage, "candidates_token_count", None) or 0
    cost = (input_tokens / 1_000_000) * PRICE_PER_M_INPUT_USD + (output_tokens / 1_000_000) * PRICE_PER_M_OUTPUT_USD
    entry = {"label": label, "input_tokens": input_tokens, "output_tokens": output_tokens, "cost_usd": cost}
    _usage_log.append(entry)
    print(
        f"[gemini cost] {label}: {input_tokens} in + {output_tokens} out tokens = "
        f"${cost:.4f}  (session total: ${total_spent_usd():.4f} / ${SESSION_BUDGET_USD:.2f})"
    )
    return entry


def summary() -> list[dict]:
    return list(_usage_log)
