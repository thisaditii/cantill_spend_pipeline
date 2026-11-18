import pandas as pd
import os
import json
from src.cleaner import load_csv_safely, calculate_net_spend, get_fx_rate
from src.rules_engine import evaluate_exclusion_rules
from src.deduplicator import deduplicate_suppliers_pipeline, deduplicate_items_pipeline
from src.classifier import MultilingualClassifier

def run_pipeline(config_path: str, data_dir: str, output_path: str):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    raw_tax_file = config.get('taxonomy_file') or config.get('taxonomy_path') or config.get('taxonomy') or 'taxonomy_B.csv'
    tax_file = os.path.basename(raw_tax_file)
    tax_path = os.path.join(data_dir, tax_file)
    tax_df = load_csv_safely(tax_path)  
    labels_path = None
    for candidate in ['classification.csv', 'seed_labels.csv', 'labels_A.csv', 'labels.csv']:
        p = os.path.join(data_dir, candidate)
        if os.path.exists(p):
            labels_path = p
            break
    train_labels_df = load_csv_safely(labels_path) if labels_path and os.path.exists(labels_path) else None
    
    classifier = MultilingualClassifier(tax_df, training_labels_df=train_labels_df)  
    fx_df = None
    fx_file_key = config.get('fx_file') or config.get('fx_rates_path') or 'fx_rates_usd.csv'
    fx_file = os.path.basename(fx_file_key)
    fx_path = os.path.join(data_dir, fx_file)
    if os.path.exists(fx_path):
        fx_df = load_csv_safely(fx_path)
            
    sources = config.get('sources')
    if not sources:
        inv_file = config.get('invoice_path') or 'invoice_lines.csv'
        sources = [{
            'file_path': os.path.basename(inv_file),
            'id_prefix': 'B' if 'B' in data_dir.upper() else 'INV',
            'id_col': 'line_id' if 'line_id' in load_csv_safely(os.path.join(data_dir, os.path.basename(inv_file))).columns else 'invoice_id',
            'date_col': 'posting_date',
            'currency_col': 'currency',
            'currency_rate_col': 'currency_rate',
            'supplier_name_col': 'vendor_id',
            'supplier_col': 'vendor_id',
            'description_cols': ['line_description', 'material_number', 'gl_account_description'],
            'po_col': 'po_number',
            'amount_col': 'line_amount',
            'vat_col': None
        }]

    output_rows = []
    seen_transactions = set() 
    
    for source in sources:
        file_path_raw = source.get('file_path', 'invoice_lines.csv')
        file_name = os.path.basename(file_path_raw)
        file_path = os.path.join(data_dir, file_name)
        
        if not os.path.exists(file_path):
            file_path = os.path.join(data_dir, file_path_raw)
            if not os.path.exists(file_path):
                continue
            
        df = load_csv_safely(file_path)
        
        amount_col = source.get('amount_col', 'line_amount')
        if amount_col not in df.columns:
            for alt in ['line_amount', 'gross_amount', 'net_amount', 'amount', 'total_amount']:
                if alt in df.columns:
                    amount_col = alt
                    source['amount_col'] = alt
                    break

        net_spends = []
        for _, row in df.iterrows():
            temp_df = pd.DataFrame([row])
            net_val = calculate_net_spend(temp_df, config, source).iloc[0]
            reporting_curr = config.get('reporting_currency', 'USD')
            curr = str(row.get(source.get('currency_col', 'currency'), reporting_curr)).upper()
            date_val = str(row.get(source.get('date_col', 'posting_date'), ''))
            
            if curr != reporting_curr and curr != '':
                rate = row.get(source.get('currency_rate_col', 'currency_rate'))
                if pd.notnull(rate) and str(rate).strip() != '' and float(rate) > 0:
                    net_val = net_val / float(rate)
                elif fx_df is not None:
                    fx = get_fx_rate(curr, date_val, fx_df)
                    net_val = net_val / fx if fx > 0 else net_val
            net_spends.append(net_val)
            
        df['calculated_spend'] = net_spends
        df['supplier_key'] = deduplicate_suppliers_pipeline(df, source.get('supplier_name_col', 'vendor_id'), source.get('supplier_col', 'vendor_id'))
        df['item_key'] = deduplicate_items_pipeline(df, source.get('description_cols', ['line_description']))
        
        supplier_name_col = source.get('supplier_name_col', 'vendor_id')
        descs = [
            f"{row.get(supplier_name_col, '')} " + " ".join([str(row.get(c, '')) for c in source.get('description_cols', ['line_description']) if pd.notnull(row.get(c))])
            for _, row in df.iterrows()
        ]
        
        id_col = source.get('id_col', 'line_id')
        if id_col not in df.columns:
            id_col = df.columns[0]
            
        record_ids = [str(row.get(id_col, f"REC_{idx}")) for idx, row in df.iterrows()]
        supplier_keys = df['supplier_key'].tolist()
        
        classifications = classifier.classify_batch(descs, record_ids=record_ids, supplier_keys=supplier_keys)
        
        for idx, row in df.iterrows():
            record_id = record_ids[idx]
            
            po = str(row.get(source.get('po_col', 'po_number'), '')).strip()
            supplier = row['supplier_key']
            item_k = row['item_key']
            amount = round(row['calculated_spend'], 2)
            
            is_dup = False
            dup_key = (po, supplier, item_k, amount)
            if po != '' and po != 'nan' and po != 'None':
                if dup_key in seen_transactions:
                    is_dup = True
                else:
                    seen_transactions.add(dup_key)
            
            include, reason = evaluate_exclusion_rules(row.to_dict(), config, source, is_duplicate=is_dup)
            spend_val = row['calculated_spend'] if include == 1 else 0.0
            cat = classifications[idx]
            
            output_rows.append({
                'record_id': record_id,
                'include': include,
                'exclusion_reason': reason,
                'supplier_key': row['supplier_key'],
                'item_key': row['item_key'],
                'spend': round(spend_val, 2),
                'l1': cat.get('l1', '') if include == 1 else '',
                'l2': cat.get('l2', '') if include == 1 else '',
                'l3': cat.get('l3', '') if include == 1 else '',
                'l4': cat.get('l4', '') if include == 1 else '',
                'confidence': cat.get('confidence', 0.0) if include == 1 else 0.0
            })
            
    out_df = pd.DataFrame(output_rows)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    out_df.to_csv(output_path, index=False)
    print(f"Pipeline executed successfully. Output saved to {output_path}")