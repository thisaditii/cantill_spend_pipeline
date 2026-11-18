# Cantill Spend Data Pipeline & Classifier

A robust, config-driven data processing, currency normalization, de-duplication, and hierarchical classification pipeline built for enterprise procurement spend analytics. Designed to ingest multi-source ERP and accounts-payable invoice data, resolve cross-system duplicates, filter non-addressable spend, and map line items to company-specific category trees.

---

## Repository Structure

```text
cantill_spend_pipeline/
│
├── configs/
│   ├── company_a.json
│   └── company_b.json
│
├── company_A/          # Raw data directory (git-ignored)
├── company_B/          # Raw data directory (git-ignored)
├── submission/
│   ├── aditi_A.csv     # Final processed output for Company A
│   └── aditi_B.csv     # Final processed output for Company B
│
├── src/                # Core pipeline modules & logic
├── main.py             # Main entry point runner
├── README.md           # Repository documentation
├── APPROACH.md         # Architecture & methodology overview
└── DECISIONS.md        # Data discoveries & engineering decisions