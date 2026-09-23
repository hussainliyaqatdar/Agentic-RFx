from .schemas import EvaluatorOutput, WorkerOutput

EXTRACTION_CONFIDENCE_THRESHOLD = 0.7
MATCH_CONFIDENCE_THRESHOLD = 0.7


def merge_lines(worker: WorkerOutput, evaluator: EvaluatorOutput) -> list[dict]:
    verdict_by_id = {v.line_id: v for v in evaluator.line_verdicts}
    merged = []
    for i, line in enumerate(worker.lines):
        verdict = verdict_by_id.get(i)
        low_confidence = line.extraction_confidence < EXTRACTION_CONFIDENCE_THRESHOLD or (
            line.match_confidence is not None and line.match_confidence < MATCH_CONFIDENCE_THRESHOLD
        )
        disputed_or_uncertain = verdict is not None and verdict.verdict != "CONFIRMED"
        record = line.model_dump()
        record["needs_review"] = line.sku_code is None or low_confidence or disputed_or_uncertain
        record["evaluator_verdict"] = verdict.verdict if verdict else "NOT_REVIEWED"
        record["evaluator_reasoning"] = verdict.reasoning if verdict else None
        record["evaluator_suggested_correction"] = verdict.suggested_correction if verdict else None
        merged.append(record)

    # Items the worker never claimed at all, but the evaluator determined are
    # actually addressable from the documents (e.g. a blanket rate never expanded
    # out). Always needs_review - these were never independently worker-verified,
    # only recovered by the second pass.
    for gap in evaluator.coverage_gaps:
        merged.append({
            "sku_code": gap.sku_code,
            "vendor_raw_description": None,
            "quantity_quoted": None,
            "unit_quoted": None,
            "unit_price_quoted": None,
            "currency_quoted": None,
            "unit_price_normalized": gap.suggested_unit_price_normalized,
            "currency_normalized": None,
            "conversion_notes": gap.suggested_conversion_notes,
            "lead_time_days": None,
            "discount_notes": None,
            "extraction_confidence": None,
            "match_confidence": None,
            "source_citation": gap.source_citation,
            "needs_review": True,
            "evaluator_verdict": "RECOVERED_BY_EVALUATOR",
            "evaluator_reasoning": gap.reasoning,
            "evaluator_suggested_correction": None,
        })
    return merged


def merge_answers(worker: WorkerOutput, evaluator: EvaluatorOutput) -> list[dict]:
    verdict_by_question = {v.question_no: v for v in evaluator.answer_verdicts}
    merged = []
    for answer in worker.answers:
        verdict = verdict_by_question.get(answer.question_no)
        disputed_or_uncertain = verdict is not None and verdict.verdict != "CONFIRMED"
        record = answer.model_dump()
        record["needs_review"] = disputed_or_uncertain or answer.confidence < EXTRACTION_CONFIDENCE_THRESHOLD
        record["evaluator_verdict"] = verdict.verdict if verdict else "NOT_REVIEWED"
        record["evaluator_reasoning"] = verdict.reasoning if verdict else None
        merged.append(record)
    return merged
