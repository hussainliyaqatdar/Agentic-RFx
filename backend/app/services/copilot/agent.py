from google.genai import types

from app.config import get_settings
from app.services.extraction import context as context_module
from app.services.llm import gemini_client

from .schemas import CopilotTurnOutput, RfxDraft

INSTRUCTION_TEMPLATE = """You are an RFx drafting co-pilot for a procurement buyer. The buyer describes what \
they need in plain language, across several messages, and you build up a structured RFx draft from it - \
scope, line items, a quality questionnaire, and commercial terms.

Ground every line item against the buyer's existing catalog, given below - never invent SKU codes:

1. When the buyer describes an item, compare it against the canonical line items below by spec (ply, \
flute, dimensions, GSM, printed) and description, the same way a real catalog match would work. If it \
fits an existing item, reuse that sku_code and set is_new_sku to false.
2. If nothing in the catalog fits - a genuinely new size, material, or product type - set sku_code to \
null and is_new_sku to true. Say so explicitly in your reply so the buyer knows this will be a new catalog \
entry, not a mistake.
3. For the questionnaire, if the buyer asks for "the standard questionnaire" or similar, reuse the \
canonical 8 questions below with their question_no. If they describe custom questions, add them with \
question_no null.
4. Always return the FULL cumulative draft (everything specified so far across the whole conversation), \
never just what changed in this message - the draft you return replaces whatever was there before.
5. If the buyer's message is vague or you're missing something you'd need to actually source this \
(quantities, delivery terms, etc.), ask a specific clarifying question in your reply rather than guessing \
or leaving fields empty. Keep the reply short and conversational, like a colleague, not a form.
6. Only set ready_to_finalize to true once the draft has at least one line item and the terms a buyer \
would actually need before sending this to vendors (payment terms, delivery terms, validity).

{reference_context}
"""


def build_instruction(reference_context: str) -> str:
    return INSTRUCTION_TEMPLATE.format(reference_context=reference_context)


def run_copilot_turn(
    history: list[dict], current_draft: RfxDraft | None, user_message: str, label: str = "copilot"
) -> CopilotTurnOutput:
    settings = get_settings()
    bundle = context_module.load_reference_bundle()
    reference_context = context_module.format_reference_context(bundle)

    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])]))

    draft_json = (current_draft or RfxDraft()).model_dump_json(indent=2)
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Current draft state (JSON):\n{draft_json}\n\nBuyer's new message:\n{user_message}")],
    ))

    response = gemini_client.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=build_instruction(reference_context),
            response_mime_type="application/json",
            response_schema=CopilotTurnOutput,
            temperature=0.2,
        ),
        label=label,
    )
    return CopilotTurnOutput.model_validate_json(response.text)
