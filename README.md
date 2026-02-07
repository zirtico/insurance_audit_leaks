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
