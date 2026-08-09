"""
Anti-hallucination guardrail for PresciMate.

The system prompt in explain.py already tells the LLM not to invent
facts, but an instruction isn't an enforcement mechanism - a model can
still confidently state a dosage or frequency that isn't actually
grounded in anything it was given. This is worth catching specifically
because a wrong dosage is the single most dangerous kind of hallucination
this app could produce.

Approach: pull every number+unit pattern (e.g. "500mg", "3 times",
"10 days") out of both the LLM's explanation and the actual source
material (the extracted prescription fields + the retrieved drug
knowledge context), and flag any number in the explanation that doesn't
appear anywhere in the source. This is a heuristic, not full semantic
verification - it won't catch a hallucinated claim that doesn't involve
a number, and it can occasionally flag a harmless rephrasing (e.g. "twice
a day" vs "2 times daily" as different tokens). It's a real, useful net
for the most dangerous failure mode, not a guarantee of zero hallucination.
"""
import re

# Numbers followed by a unit-ish word: mg, ml, mcg, g, times, days,
# hours, tablets, drops, etc. - covers the dosage/frequency/duration
# vocabulary this app actually deals with.
_NUMBER_UNIT_RE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*"
    r"(mg|mcg|ml|g|gram|grams|tablet|tablets|capsule|capsules|drop|drops|"
    r"time|times|day|days|hour|hours|week|weeks|dose|doses)\b",
    re.IGNORECASE,
)


def _extract_number_units(text: str) -> set[str]:
    """Returns a set of normalized 'number+unit' tokens found in text,
    e.g. {"650mg", "3times", "5days"}."""
    if not text:
        return set()
    matches = _NUMBER_UNIT_RE.findall(text)
    return {f"{num}{unit.lower()}" for num, unit in matches}


def check_grounding(explanation: str, medicines: list[dict], drug_context: str) -> dict:
    """Checks whether every number+unit claim in the explanation is
    grounded in the source material. Returns:
        {"flagged": bool, "ungrounded_claims": list[str]}
    `flagged=True` means at least one number in the explanation doesn't
    appear anywhere in the prescription data or retrieved context - worth
    a warning, not necessarily wrong, but not verifiable either."""
    source_text = drug_context + "\n" + "\n".join(
        f"{m.get('dosage') or ''} {m.get('frequency') or ''} {m.get('duration') or ''}"
        for m in medicines
    )

    source_tokens = _extract_number_units(source_text)
    explanation_tokens = _extract_number_units(explanation)

    ungrounded = sorted(explanation_tokens - source_tokens)
    return {"flagged": bool(ungrounded), "ungrounded_claims": ungrounded}
