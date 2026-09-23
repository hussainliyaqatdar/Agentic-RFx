from pathlib import Path

from app.config import get_settings

from . import context as context_module
from .document_loader import load_vendor_documents
from .evaluator import run_evaluator
from .merge import merge_answers, merge_lines
from .worker import run_worker


def run_pipeline_for_vendor(vendor_slug: str) -> dict:
    """Runs the full worker -> evaluator -> merge loop for one vendor's response
    folder under <seed_data_dir>/vendors/<vendor_slug>/. Makes real Gemini calls."""
    settings = get_settings()
    vendor_dir = Path(settings.seed_data_dir) / "vendors" / vendor_slug
    document_parts = load_vendor_documents(vendor_dir)

    bundle = context_module.load_reference_bundle()
    reference_context = context_module.format_reference_context(bundle)

    worker_output = run_worker(reference_context, document_parts, label=f"worker:{vendor_slug}")
    evaluator_output = run_evaluator(reference_context, document_parts, worker_output, label=f"evaluator:{vendor_slug}")

    return {
        "vendor_slug": vendor_slug,
        "lines": merge_lines(worker_output, evaluator_output),
        "answers": merge_answers(worker_output, evaluator_output),
        "evaluator_overall_notes": evaluator_output.overall_notes,
    }
