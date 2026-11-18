import pandas as pd
import hashlib

def normalize_supplier_name(name: str) -> str:
    if not name or str(name).strip() == '':
        return 'UNKNOWN'
    s = str(name).lower().strip()
    suffixes = ['pty', 'ltd', 'limited', 'inc', 'llc', 'corp', 'corporation', 'ag', 'gmbh']
    tokens = [t for t in s.split() if t not in suffixes]
    return " ".join(tokens)

def generate_stable_key(prefix: str, text: str) -> str:
    hasher = hashlib.md5(text.encode('utf-8'))
    return f"{prefix}-{hasher.hexdigest()[:7]}"

def deduplicate_suppliers_pipeline(df: pd.DataFrame, name_col: str, id_col: str = None) -> pd.Series:
    keys = []
    normalized_map = {}
    for _, row in df.iterrows():
        base_id = str(row.get(id_col, '')).strip() if id_col else ''
        raw_name = str(row.get(name_col, '')).strip()
        identifier = base_id if base_id and base_id != 'nan' else normalize_supplier_name(raw_name)
        if identifier not in normalized_map:
            normalized_map[identifier] = generate_stable_key("SG", identifier)
        keys.append(normalized_map[identifier])
    return pd.Series(keys, index=df.index)

def deduplicate_items_pipeline(df: pd.DataFrame, desc_cols: list) -> pd.Series:
    keys = []
    item_map = {}
    for _, row in df.iterrows():
        desc = " ".join([str(row.get(c, '')) for c in desc_cols]).lower().strip()
        clean_desc = ''.join([c if c.isalnum() else ' ' for c in desc])
        clean_desc = " ".join(clean_desc.split())
        if not clean_desc:
            clean_desc = "unknown_item"
        if clean_desc not in item_map:
            item_map[clean_desc] = generate_stable_key("IG", clean_desc)
        keys.append(item_map[clean_desc])
    return pd.Series(keys, index=df.index)