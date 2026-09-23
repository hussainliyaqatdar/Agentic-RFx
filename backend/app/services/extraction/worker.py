from google.genai import types

from app.config import get_settings
from app.services.llm import gemini_client

from .schemas import WorkerOutput

INSTRUCTION_TEMPLATE = """You are a procurement extraction agent. You are given every document one vendor \
sent in response to an RFx, in whatever raw format they used - a spreadsheet, a PDF, a Word document, a \
photo of a printed rate card, or plain email text - sometimes more than one document for the same vendor.

Using ONLY what is actually in the documents:

1. If there are multiple documents for this vendor, a later or more explicit statement (e.g. a follow-up \
email) can override or supplement an earlier one (e.g. an initial rate card photo). Use the most current \
statement when they conflict, and say so in conversion_notes.
2. For every line the vendor quoted, match it to a canonical SKU below by comparing specs (ply, flute, \
dimensions, GSM, printed) and description - never assume the vendor's own code or row order lines up with \
the canonical list. If a vendor line doesn't correspond to any canonical item, leave sku_code null rather \
than forcing a match. If a canonical item is never addressed anywhere in this vendor's documents, do not \
invent a line for it.
3. Record the vendor's numbers exactly as stated (unit_price_quoted, unit_quoted, currency_quoted), then \
separately compute unit_price_normalized and currency_normalized in the RFx's canonical unit and currency. \
Explain any conversion in conversion_notes: unit conversion (e.g. per-kg to per-box using the item's weight \
from the spec below, per-100-pieces to per-box), currency conversion using the reference FX rate given \
below, and any discount - state the condition you checked (e.g. a quantity threshold in a footnote) and \
whether it applied to this specific line.
4. If the vendor says something like "rest same as last year" or similar, resolve those specific lines \
against the reference/last-year price shown for that SKU below, and say so explicitly in conversion_notes.
5. Answer every questionnaire question you find an answer for, referencing it by question_no. Omit a \
question entirely if the vendor didn't answer it anywhere - never guess an answer to fill a gap.
6. Give every line and every answer a source_citation naming the document and a short quoted snippet or \
location (page/cell/paragraph), and a confidence score that reflects real uncertainty - not a default 1.0 \
for everything.

Never invent a number that isn't grounded in the documents. If you're not sure, say so via a lower \
confidence rather than rounding up.

{reference_context}
"""


def build_worker_instruction(reference_context: str) -> str:
    return INSTRUCTION_TEMPLATE.format(reference_context=reference_context)


def run_worker(reference_context: str, document_parts: list, label: str = "worker") -> WorkerOutput:
    settings = get_settings()
    response = gemini_client.generate_content(
        model=settings.gemini_model,
        contents=document_parts,
        config=types.GenerateContentConfig(
            system_instruction=build_worker_instruction(reference_context),
            response_mime_type="application/json",
            response_schema=WorkerOutput,
            temperature=0.1,
        ),
        label=label,
    )
    return WorkerOutput.model_validate_json(response.text)
