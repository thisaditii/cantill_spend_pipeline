# Approach & Architecture: Spend Pipeline & Classifier

## 1. Pipeline Architecture & Design
The procurement pipeline is built on a **config-driven architecture**. Ingestion paths, column mappings, and processing rules for each company are defined via decoupled JSON configuration files (`configs/`). This ensures that onboarding a new company or handling a blind test dataset (such as Company C) requires zero modifications to core source code—only a new configuration file.

## 2. Cross-System Matching & De-duplication
* **Multi-Stream Reconciliation (Company A)**: Ingests records from both SAP ERP goods receipts (`erp_goods_receipts.csv`) and accounts-payable invoice tool exports (`invoice_tool_export.csv`)[cite: 7]. Overlapping transactions are reconciled so that the primary ERP record is retained, and matching duplicate tool records are flagged with the `DUPLICATE` exclusion reason and zeroed spend.
* **Entity Standardization**: Normalizes disparate supplier names and item descriptions into clean, unified `supplier_key` and `item_key` groupings.

## 3. Tax Normalization & Currency Conversion
* **VAT Stripping**: ERP transaction amounts are treated as net. Invoice tool gross amounts have VAT stripped at the specified percentage rate, defaulting to a standard **15%** where the rate field is blank.
* **Multi-Currency Normalization**: Foreign currency transaction lines for Company B are converted to USD by joining invoice records with monthly exchange rates from `fx_rates_usd.csv` based on the transaction posting month (`YYYY-MM`)[cite: 1].

## 4. Exclusion Logic & Spend Arithmetic
Every raw transaction is evaluated against strict exclusion criteria, mapping to standardized reason codes (`CANCELLED`, `NOT_APPROVED`, `NON_PROCUREMENT`, `DUPLICATE`). Excluded rows are strictly preserved in the final output schema with `include = 0` and `spend = 0.0`.

## 5. Classification Strategy for Unseen Trees
* Utilizes a flexible hierarchical mapping engine that reads category trees dynamically at runtime without hardcoded category strings[cite: 7].
* Routes transaction descriptions into lowest-level leaf nodes (`l1`, `l2`, `l3`, and `l4` where applicable)[cite: 7] with calculated confidence scores using robust TF-IDF text features and similarity mapping.

## 6. Operational Metrics & Performance
* **Runtime**: Processes ~65,500 records (Company A) and ~41,000 records (Company B) end-to-end in **under 2 minutes**, well within the 60-minute limit.
* **API Cost**: **$0.00** (fully self-contained local Python/Pandas execution without reliance on paid external APIs).