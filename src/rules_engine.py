import pandas as pd

def evaluate_exclusion_rules(row: dict, config: dict, source_conf: dict, is_duplicate: bool = False) -> tuple:
    status_col = source_conf.get('status_col')
    status = str(row.get(status_col, '')).strip().lower() if status_col else ''
    
    approved_statuses = [s.lower() for s in source_conf.get('approved_statuses', ['approved', 'paid', 'complete', 'completed', 'active', 'ok', '1'])]
    cancelled_statuses = [s.lower() for s in source_conf.get('cancelled_statuses', ['cancelled', 'void', 'canceled'])]
    rejected_statuses = ['rejected', 'declined', 'on-hold', 'draft', 'pending', 'unapproved', 'in review', 'suspended', '0']
    
    if status in cancelled_statuses or 'cancel' in status or 'void' in status:
        return 0, 'CANCELLED'
        
    if status in rejected_statuses or (status != '' and status not in approved_statuses):
        return 0, 'NOT_APPROVED'
    desc_cols = source_conf.get('description_cols', [])
    desc = " ".join([str(row.get(col, '')) for col in desc_cols]).lower()
    supplier_name = str(row.get(source_conf.get('supplier_name_col', ''), '')).lower()
    full_text = f"{desc} {supplier_name}"
    
    non_proc_keywords = config.get('exclusion_keywords', ['tax', 'vat', 'intercompany', 'royalty', 'interest', 'revenue', 'dividend', 'financing', 'gst', 'customs duty'])
    for kw in non_proc_keywords:
        if kw in full_text:
            return 0, 'NON_PROCUREMENT'
            
    if is_duplicate:
        return 0, 'DUPLICATE'
        
    return 1, ''