"""
Misclassification Analysis (Payroll Rows -> Flags)
==================================================
Uses a local LLM when available; falls back to the keyword-based detector.
"""

from typing import Any, Dict, List, Optional
import json

from llm_provider import BaseLLMProvider, default_provider
from misclassification_detector import analyze_payroll_for_misclassifications


def build_misclassification_prompt(payroll_rows: List[Dict[str, Any]]) -> str:
    return "\n".join(
        [
            "You are a workers' comp class code auditor.",
            "Given payroll rows, identify likely misclassifications.",
            "Use language understanding for job titles vs class codes.",
            "Return JSON with a 'flags' array shaped like misclassification_detector.MisclassificationFlag.to_dict().",
            json.dumps(payroll_rows, indent=2),
        ]
    )


def analyze_misclassifications(
    payroll_rows: List[Dict[str, Any]],
    provider: Optional[BaseLLMProvider] = None
) -> List[Dict[str, Any]]:
    if not payroll_rows:
        return []
    provider = provider or default_provider()
    prompt = build_misclassification_prompt(payroll_rows)
    response = provider.generate(prompt)
    if not response.used_fallback and response.content.strip():
        try:
            payload = json.loads(response.content)
            flags = payload.get("flags")
            if isinstance(flags, list):
                return flags
        except (json.JSONDecodeError, TypeError):
            pass

    fallback_flags = analyze_payroll_for_misclassifications(payroll_rows)
    return [flag.to_dict() for flag in fallback_flags]
