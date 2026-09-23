import json

from google.genai import types

from app.config import get_settings
from app.services.llm import gemini_client

from .schemas import EvaluatorOutput, WorkerOutput

INSTRUCTION_TEMPLATE = """You are a skeptical quality auditor reviewing another agent's extraction of a \
vendor's RFx response, for a buyer who may act on these numbers with real money. Your job is to find what \
is wrong, not to confirm what looks right.

You are given the same source documents the other agent saw, and its claimed output as JSON (each line \
tagged with a line_id, each answer tagged with a question_no). For every claimed line and answer:

1. Re-derive the value yourself from the documents - don't just check whether the claim looks plausible. \
If the claimed sku_code doesn't fit the vendor's stated spec/description as well as some other canonical \
item (or no item at all), dispute it and explain which SKU you think actually fits, if any.
2. Check that every number (price, quantity, unit) is actually stated in a document, not inferred beyond \
what the text supports.
3. Independently redo any conversion math - unit conversion, currency conversion using the reference FX \
rate, discount conditions - and check it matches what was claimed. Recompute it yourself rather than \
trusting the other agent's conversion_notes.
4. If you cannot verify a claim either way from what's in the documents (e.g. an illegible part of a \
photo, or genuinely ambiguous phrasing), mark it UNCERTAIN rather than CONFIRMED - do not give the benefit \
of the doubt.
5. Then check completeness, not just correctness of what was claimed: go through the full canonical line \
item list below and check whether the documents actually contain enough information to price any item the \
other agent did NOT claim at all. This matters most when a vendor states a general rule rather than a \
line-by-line list - a rate that applies to a whole category ("₹42/kg for the 5-ply"), or a statement like \
"rest same as last year" that resolves against the reference price below. If the other agent only extracted \
a few literal rows and never expanded a stated rule out across the items it actually covers, that is a real \
gap - list every such SKU in coverage_gaps with your own best-effort price and reasoning. Only flag items \
you can actually justify from what's in front of you; do not invent coverage that isn't there.

Give every verdict a one-sentence reasoning. For DISPUTED verdicts, include suggested_correction with the \
value you believe is correct, if you can determine it.

{reference_context}
"""


def build_evaluator_instruction(reference_context: str) -> str:
    return INSTRUCTION_TEMPLATE.format(reference_context=reference_context)


def _serialize_claimed_output(worker_output: WorkerOutput) -> str:
    claimed = {
        "lines": [{"line_id": i, **line.model_dump()} for i, line in enumerate(worker_output.lines)],
        "answers": [answer.model_dump() for answer in worker_output.answers],
    }
    return "The other agent's claimed extraction (JSON):\n" + json.dumps(claimed, indent=2)


def run_evaluator(
    reference_context: str, document_parts: list, worker_output: WorkerOutput, label: str = "evaluator"
) -> EvaluatorOutput:
    settings = get_settings()
    contents = [*document_parts, _serialize_claimed_output(worker_output)]
    response = gemini_client.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=build_evaluator_instruction(reference_context),
            response_mime_type="application/json",
            response_schema=EvaluatorOutput,
            temperature=0.1,
        ),
        label=label,
    )
    return EvaluatorOutput.model_validate_json(response.text)
