"""
Audit Letter Generator (Engine Output -> Draft Letter)
======================================================
Free baseline: deterministic template with optional local LLM refinement.
"""

from typing import Any, Dict, List, Optional

from llm_provider import BaseLLMProvider, default_provider


def _format_currency(value: float) -> str:
    return f"${value:,.2f}"


def _leak_bullets(leaks: List[Dict[str, Any]]) -> str:
    lines = []
    for leak in leaks:
        impact = _format_currency(leak.get("dollar_impact", 0.0))
        lines.append(f"- {leak.get('type')}: {impact} — {leak.get('description')}")
    return "\n".join(lines) if lines else "- No leaks detected."


def build_letter_template(
    audit_json: Dict[str, Any],
    misclassification_flags: Optional[List[Dict[str, Any]]] = None
) -> str:
    policy_number = audit_json.get("policy_number", "")
    state = audit_json.get("state", "")
    current_mod = audit_json.get("current_mod", "")
    corrected_mod = audit_json.get("corrected_mod", "")
    mod_reduction = audit_json.get("mod_reduction", "")
    premium_savings = _format_currency(audit_json.get("premium_savings", 0.0))
    total_leak_impact = _format_currency(audit_json.get("total_leak_impact", 0.0))

    leaks = audit_json.get("leaks", [])
    misclassification_flags = misclassification_flags or []
    misclass_section = ""
    if misclassification_flags:
        misclass_lines = "\n".join(
            f"- {flag.get('employee_name')}: {flag.get('current', {}).get('code')} -> "
            f"{flag.get('suspected', {}).get('code')} ({flag.get('detection', {}).get('confidence')})"
            for flag in misclassification_flags
        )
        misclass_section = f"\nPotential classification issues (manual review required):\n{misclass_lines}\n"

    return f"""Subject: Experience Mod Audit Findings — Policy {policy_number}

To Whom It May Concern,

We completed a review of the experience rating data for policy {policy_number} ({state}).
Our analysis shows the current mod of {current_mod} should be corrected to {corrected_mod},
resulting in a mod reduction of {mod_reduction} and estimated premium savings of {premium_savings}.

Total leak impact identified: {total_leak_impact}

Key findings:
{_leak_bullets(leaks)}
{misclass_section}

We request that these items be reviewed and corrected per the applicable rating rules.
Please confirm receipt and advise on next steps.

Sincerely,
"""


def build_letter_prompt(
    audit_json: Dict[str, Any],
    misclassification_flags: Optional[List[Dict[str, Any]]] = None
) -> str:
    return "\n".join(
        [
            "Draft a professional workers' compensation audit letter.",
            "Use the provided audit JSON for facts.",
            "Keep it concise, formal, and list key findings with dollar impacts.",
            "If misclassification flags are provided, include a short manual-review section.",
            "Return the full letter text only.",
            str(audit_json),
            f"misclassification_flags={misclassification_flags or []}",
        ]
    )


def generate_audit_letter(
    audit_json: Dict[str, Any],
    misclassification_flags: Optional[List[Dict[str, Any]]] = None,
    provider: Optional[BaseLLMProvider] = None
) -> str:
    provider = provider or default_provider()
    prompt = build_letter_prompt(audit_json, misclassification_flags)
    response = provider.generate(prompt)
    if response.used_fallback or not response.content.strip():
        return build_letter_template(audit_json, misclassification_flags)
    return response.content.strip()
