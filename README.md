# insurance_audit_leaks

Logic engine first by state, LLM parser and output layer to follow.

## Ingestion → LLM → Engine Contract (Draft)

`ingest_files.py` produces OCR-backed markdown plus table data for an LLM
normalization step. The LLM should output structured JSON aligned to:

- `PolicyInfo`, `ClassCodeExposure`, `Claim` in `mod_engine.py` for the audit
  engine inputs.
- Payroll rows shaped like `{"employee_name","job_title","class_code","annual_payroll","job_duties?"}`
  for the misclassification detector.

This keeps the OCR/vision layer deterministic and avoids hallucinated values
before the engine computes mod impact and premium savings.

### Mapping Guidance File

See `llm_mapping.py` for:
- Required field groups per document type (loss runs, payroll journals, SUI).
- Field synonym guidance for fuzzy header matching.
- Normalized payload schemas that align to the engine.
- Mapping rules for loss-run semantic normalization, status inference,
  entity reconciliation, and math validation guardrails.

The synonym list is intended as a fallback/validation aid; the LLM should still
use language understanding for fuzzy header mapping and job-title alignment.

## LLM Layers (Free Baseline)

- `llm_normalizer.py`: deterministic OCR → JSON normalization with an optional
  local LLM (Ollama) fallback for richer mapping.
- `llm_audit_letters.py`: generates audit-letter drafts from `mod_engine`
  output, using a template by default and optional local LLM refinement.
- `llm_provider.py`: minimal provider wrapper (uses Ollama if installed).
- `run_pipeline.py`: end-to-end runner that connects ingestion, normalization,
  engine calculation, and letter drafting.
- `llm_misclassification.py`: optional LLM-backed misclassification analysis
  with fallback to keyword heuristics.

When normalization errors or row-level validation flags occur, the pipeline
now emits `review_report.json` and stops for manual review.

The pipeline runner logs each stage, writes a structured error report if
ingestion/engine/letter stages fail, and can optionally write the letter to a
file: `python run_pipeline.py <path_to_pdf> <output_path>`.
