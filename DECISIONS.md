# Data Discoveries & Engineering Decisions

## 1. Handling Date Parsing Anomalies
* **Discovery**: Raw transaction and invoice date fields contained mixed string formats, leading whitespace, and occasional corrupted or blank entries.
* **Decision**: Utilized `pd.to_datetime` with `errors='coerce'` to safely parse dates, extracting standard `YYYY-MM` accounting periods to ensure robust monthly FX rate joins without causing pipeline runtime crashes.

## 2. Defaulting Missing Tax Rates
* **Discovery**: Several accounts-payable invoice lines in Company A lacked explicit VAT percentage values.
* **Decision**: Implemented the brief's standard rule: where the VAT rate is blank or missing, a default tax rate of **15%** is applied to correctly derive net spend from gross invoice amounts.

## 3. Preserving Excluded Records in Full Output
* **Discovery**: Initial pipeline iterations filtered out non-addressable rows, reducing row counts below source totals.
* **Decision**: Enforced strict **Section 6 compliance**: all input records (including cancelled, unapproved, and duplicate lines) are retained in the final CSV output, with `include = 0` and `spend = 0.0`.

## 4. Entity Key Harmonization
* **Discovery**: Vendor identifiers and material item codes varied widely across multiple regional ERP systems in Company B.
* **Decision**: Mapped raw vendor codes to standardized `supplier_key` attributes and material numbers to `item_key` fields to maintain analytical consistency across category spend cubes.