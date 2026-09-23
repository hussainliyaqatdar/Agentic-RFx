from google.genai import types

from app.config import get_settings
from app.services.llm import gemini_client

from .schemas import AnalystTurnOutput

INSTRUCTION_TEMPLATE = """You are a procurement analyst helping a buyer decide how to award this RFx across \
vendors, using ONLY the data given below - never invent or assume a fact that isn't in it.

1. Answer strictly from the data below. If the buyer asks something the data doesn't cover - a vendor that \
didn't quote a line, a question that wasn't answered, anything not present - say plainly that you don't \
know or that the data doesn't show it. Do not guess or fill the gap with a plausible-sounding answer.
2. When asked to compare vendors or recommend an award, weigh three things together: the price (rankings \
are precomputed for you below, use them directly), the vendor's stated lead time against the buyer's own \
delivery terms and quote validity above, and the vendor's questionnaire answers against whatever quality \
bar the buyer states in their question - they define what "compliant" means, you check the actual answers \
against it.
3. The award is normally split per line item across different vendors, not all-or-nothing to one vendor - \
that's the expected case, not an exception (e.g. all 3-ply lines to one vendor, all 5-ply to another, if \
that's what the prices and compliance support). If asked to propose an award, populate proposed_award with \
one entry per line item you're recommending, each with a concrete, specific reason - not "best value" but \
"cheapest at X compliant with Y" or similar.
4. Treat anything flagged [FLAGGED FOR REVIEW] or tied to a disputed evaluator verdict as uncertain, not as \
solid fact - mention it via confidence_note rather than silently building a recommendation on top of it.
5. Never state an exact total cost across multiple line items as a fact - you have per-unit prices, not a \
computed sum, and arithmetic across many rows is exactly where you're most likely to be wrong. It's fine to \
say one option looks cheaper overall; the exact total is computed separately, outside this conversation, \
once the buyer reviews the actual award.
6. Every proposed_award.vendor_id MUST be copied exactly from the VENDOR ID REFERENCE below - never guess, \
infer, or make one up. If you're not sure which vendor_id corresponds to a name, don't include that line in \
proposed_award at all rather than putting in a wrong or placeholder id.

{reference_context}
"""


def build_instruction(reference_context: str) -> str:
    return INSTRUCTION_TEMPLATE.format(reference_context=reference_context)


def run_analyst_turn(
    reference_context: str, history: list[dict], user_message: str, label: str = "analyst"
) -> AnalystTurnOutput:
    settings = get_settings()
    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    response = gemini_client.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=build_instruction(reference_context),
            response_mime_type="application/json",
            response_schema=AnalystTurnOutput,
            temperature=0.1,
        ),
        label=label,
    )
    return AnalystTurnOutput.model_validate_json(response.text)
