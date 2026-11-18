import pandas as pd
import numpy as np

def load_csv_safely(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path, dtype=str, keep_default_na=False)

def parse_amount(val) -> float:
    if val is None or str(val).strip() == '':
        return 0.0
    s = str(val).strip()
    is_negative = False
    if s.startswith('(') and s.endswith(')'):
        is_negative = True
        s = s[1:-1]
    if s.endswith('-'):
        is_negative = True
        s = s[:-1].strip()
    cleaned = ''.join([c for c in s if c.isdigit() or c in ['.', '-']])
    try:
        val_float = float(cleaned)
        return -val_float if is_negative else val_float
    except ValueError:
        return 0.0

def parse_vat(vat_val, default_vat=0.15) -> float:
    if vat_val is None or str(vat_val).strip() == '':
        return default_vat
    s = str(vat_val).strip().replace('%', '')
    try:
        val = float(s)
        if val > 1.0:
            val = val / 100.0
        return val
    except ValueError:
        return default_vat

def calculate_net_spend(df: pd.DataFrame, config: dict, source_conf: dict) -> pd.Series:
    amounts = df[source_conf['amount_col']].apply(parse_amount)
    basis = source_conf.get('amount_basis', 'net')
    if basis == 'gross':
        vat_col = source_conf.get('vat_col')
        default_vat = source_conf.get('default_vat', 0.15)
        vat_rates = df[vat_col].apply(lambda x: parse_vat(x, default_vat)) if vat_col and vat_col in df.columns else default_vat
        return amounts / (1.0 + vat_rates)
    return amounts

def get_fx_rate(currency: str, date_str: str, fx_df: pd.DataFrame) -> float:
    curr = str(currency).upper()
    if curr == 'USD' or curr == '' or fx_df is None or fx_df.empty:
        return 1.0
    month_key = str(date_str)[:7]
    curr_fx = fx_df[fx_df['currency'].str.upper() == curr].copy()
    if curr_fx.empty:
        return 1.0
    curr_fx['month_key'] = curr_fx['month'].astype(str).str[:7]
    match = curr_fx[curr_fx['month_key'] == month_key]
    if not match.empty:
        return float(match.iloc[0]['units_per_usd'])
    return 1.0