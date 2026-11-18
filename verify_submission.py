import os
import json
import pandas as pd

def audit_pipeline():
    print("=== STARTING AUTOMATED SUBMISSION AUDIT ===")
    errors = 0
    warnings = 0
    print("\n[1] Checking Directory Structure & Configs...")
    required_dirs = ['configs', 'submission']
    for d in required_dirs:
        if os.path.exists(d):
            print(f"  ✅ Directory '{d}/' exists.")
        else:
            print(f"  ❌ Missing required directory: '{d}/'")
            errors += 1
    config_files = [f for f in os.listdir('configs') if f.endswith(('.json', '.yaml', '.yml'))] if os.path.exists('configs') else []
    if len(config_files) >= 2:
        print(f"  ✅ Found config files: {config_files}")
    else:
        print(f"  ⚠️ Warning: Found fewer than 2 config files in 'configs/'. Make sure Company A and B are config-driven.")
        warnings += 1

    print("\n[2] Checking Output Files in submission/...")
    required_outputs = ['submission/aditi_A.csv', 'submission/aditi_B.csv']
    for file_path in required_outputs:
        if os.path.exists(file_path):
            print(f"  ✅ Output file exists: {file_path}")
        else:
            print(f"  ❌ Missing output file: {file_path}")
            errors += 1
    print("\n[3] Validating Output Column Schemas...")
    expected_columns = [
        'record_id', 'include', 'exclusion_reason', 
        'supplier_key', 'item_key', 'spend', 
        'l1', 'l2', 'l3', 'confidence'
    ]

    for file_path in required_outputs:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"\n  Inspecting {file_path} (Total Rows: {len(df)}):")
            
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if not missing_cols:
                print(f"    ✅ All required Section 6 columns present.")
            else:
                print(f"    ❌ Missing columns in {file_path}: {missing_cols}")
                errors += 1

            if 'include' in df.columns and 'spend' in df.columns:
                excluded_rows = df[df['include'] != 1]
                non_zero_spend_exclusions = excluded_rows[excluded_rows['spend'] > 0]
                if len(non_zero_spend_exclusions) == 0:
                    print(f"    ✅ Spend rule verified: All excluded rows have 0 spend.")
                else:
                    print(f"    ❌ Error: {len(non_zero_spend_exclusions)} excluded rows have spend > 0!")
                    errors += 1
    print("\n[4] Checking Required Documentation Files...")
    required_docs = ['README.md', 'APPROACH.md', 'DECISIONS.md']
    for doc in required_docs:
        if os.path.exists(doc):
            print(f"  ✅ Found documentation: {doc}")
        else:
            print(f"  ❌ Missing documentation file: {doc}")
            errors += 1

    print("\n=== AUDIT SUMMARY ===")
    if errors == 0:
        print(f" SUCCESS! No critical errors found. Your submission package looks solid (Warnings: {warnings}).")
    else:
        print(f"❌ AUDIT FAILED with {errors} error(s) and {warnings} warning(s). Please fix the items marked with ❌.")

if __name__ == "__main__":
    audit_pipeline()