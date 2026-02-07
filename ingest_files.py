"""
Docling Ingestion Pipeline (Free / Open Source)
===============================================
Role: The "Eyes" of the system (Free Tier).
Input: Raw PDF (Loss Run, Payroll, ERW).
Output: Clean MARKDOWN + Summation Validation.

Prerequisites:
  pip install docling pandas
"""

import os
import re
import pandas as pd
from typing import Dict, List, Any
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

class DoclingIngestionEngine:
    def __init__(self):
        """
        Initialize the Docling engine with table-structure optimization.
        This runs LOCALLY. No API keys required.
        """
        # Configure pipeline to prioritize table structure accuracy
        pipeline_options = PdfPipelineOptions(
            do_table_structure=True,
            do_ocr=True,  # Set False if you are 100% sure PDFs are digital-native to speed it up
            table_structure_options={"mode": TableFormerMode.ACCURATE} # Best for loss runs
        )
        
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: pipeline_options}
        )

    def analyze_document(self, file_path: str) -> Dict:
        """
        Main entry point. Sends PDF to local Docling model.
        Returns 'ForensicArtifact' dictionary ready for the LLM.
        """
        print(f"[*] Processing {os.path.basename(file_path)} with Docling (Local)...")
        
        try:
            # 1. Conversion (The Heavy Lifting)
            doc_result = self.converter.convert(file_path)
            document = doc_result.document
            
            # 2. Extract Tables to Pandas (for deterministic summation checks)
            dfs = self._extract_tables_to_pandas(document)
            
            # 3. Convert to Markdown (The "Bridge" for the LLM)
            # Docling's markdown export is SOTA for preserving table structure
            markdown_text = document.export_to_markdown()
            
            # 4. Run Pre-LLM Summation Check (Leak #20)
            # We assume the "raw text" for regex search is the markdown export
            summation_audit = self._audit_column_totals(dfs, markdown_text)

            return {
                "status": "SUCCESS",
                "raw_text": markdown_text, # Docling treats markdown as the text representation
                "markdown_content": markdown_text,
                "tables_data": [df.to_dict() for df in dfs],
                "summation_audit": summation_audit,
                "metadata": {
                    "page_count": len(document.pages),
                    "model_used": "docling-tableformer"
                }
            }
            
        except Exception as e:
            return {
                "status": "FAILED",
                "reason": str(e),
                "details": "Docling conversion failed. Ensure PyTorch is installed."
            }

    def _extract_tables_to_pandas(self, document: Any) -> List[pd.DataFrame]:
        """
        Iterates through Docling's detected table objects and converts to Pandas.
        """
        dataframes = []
        
        # Docling stores tables in document.tables
        for table in document.tables:
            try:
                # Docling has a built-in method for this
                df = table.export_to_dataframe()
                
                # Basic cleaning: Replace NaNs with empty string
                df = df.fillna("")
                
                # Convert all columns to string to match logic expectations
                df = df.astype(str)
                
                dataframes.append(df)
            except Exception as e:
                print(f"[-] Warning: Failed to convert a table to DataFrame: {e}")
                continue
                
        return dataframes

    def _audit_column_totals(self, dfs: List[pd.DataFrame], raw_text: str) -> Dict:
        """
        Forensic Step: Leak #20 (Clerical Mix-up).
        Sums the 'Incurred' column from the tables and looks for a 'Grand Total' in text.
        """
        audit_log = []
        
        # 1. Try to find the "Total" in the raw text using Regex
        total_pattern = r"(?:Grand Total|Total Incurred|Report Total)[\s:$]*([\d,]+\.\d{2})"
        matches = re.findall(total_pattern, raw_text, re.IGNORECASE)
        
        doc_claimed_total = 0.0
        if matches:
            # Take the last one found (usually at the bottom)
            clean_str = matches[-1].replace(",", "")
            try:
                doc_claimed_total = float(clean_str)
            except:
                pass

        # 2. Sum the columns in the DataFrame
        math_calculated_total = 0.0
        
        for i, df in enumerate(dfs):
            for col in df.columns:
                # Flexible matching for Loss Run headers
                header = str(col).lower()
                if "incurred" in header or "total" in header or "amount" in header:
                    # Don't sum columns that look like dates or claim numbers
                    if "date" in header or "claim" in header:
                        continue
                        
                    try:
                        # Clean currency strings: "$1,234.56" -> 1234.56
                        # Remove '(', ')' for accounting negatives if present
                        numeric_series = df[col].astype(str).str.replace(r'[$,]', '', regex=True)
                        numeric_series = numeric_series.str.replace(r'[(]', '-', regex=True).str.replace(r'[)]', '', regex=True)
                        
                        numeric_series = pd.to_numeric(numeric_series, errors='coerce').fillna(0)
                        col_sum = numeric_series.sum()
                        
                        # Heuristic: If sum is substantial, it's likely a financial column
                        if col_sum > 1000: 
                            math_calculated_total += col_sum
                            audit_log.append(f"Table {i+1} Column '{col}': Sum = ${col_sum:,.2f}")
                    except:
                        continue

        # 3. Compare
        variance = 0.0
        if doc_claimed_total > 0:
            variance = abs(math_calculated_total - doc_claimed_total)
            status = "PASS" if variance < 5.0 else "FAIL" # $5 rounding tolerance
        else:
            status = "SKIPPED" # Couldn't find a footer total to check against
            
        return {
            "status": status,
            "ocr_calculated_sum": math_calculated_total,
            "document_printed_total": doc_claimed_total,
            "variance": variance,
            "details": audit_log
        }

# ═══════════════════════════════════════════════════════════════════════════
# EXECUTION STUB
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Test Run
    import sys
    
    # Check if docling is installed
    try:
        import docling
    except ImportError:
        print("CRITICAL: You must install docling first.")
        print("Run: pip install docling pandas")
        sys.exit(1)

    print("Initializing Docling Engine...")
    engine = DoclingIngestionEngine()
    print(">> Engine Ready. Call engine.analyze_document(pdf_path)")
