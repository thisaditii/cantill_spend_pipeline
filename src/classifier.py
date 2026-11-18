import pandas as pd
import numpy as np
import torch
import re
from sentence_transformers import SentenceTransformer, util

class MultilingualClassifier:
    def __init__(self, taxonomy_df: pd.DataFrame, training_labels_df: pd.DataFrame = None):
        self.taxonomy = taxonomy_df
        self.cat_cols = [c for c in taxonomy_df.columns if any(k in c.lower() for k in ['l1', 'l2', 'l3', 'l4', 'category'])]
        
        self.l1_col = self.cat_cols[0] if len(self.cat_cols) > 0 else None
        self.l2_col = self.cat_cols[1] if len(self.cat_cols) > 1 else None
        self.l3_col = self.cat_cols[2] if len(self.cat_cols) > 2 else None
        
        self.unique_l1s = taxonomy_df[self.l1_col].dropna().unique().tolist() if self.l1_col else []
        self.l1_texts = [f"Procurement category L1: {l1}" for l1 in self.unique_l1s]
        self.category_records = []
        self.category_texts = []
        for _, row in taxonomy_df.iterrows():
            parts = [str(row[col]) for col in self.cat_cols if pd.notnull(row[col]) and str(row[col]).strip() != '' and str(row[col]).lower() != 'nan']
            cat_str = f"Procurement category for {' > '.join(parts)}"
            self.category_texts.append(cat_str)
            self.category_records.append({col: row[col] for col in self.cat_cols})
            
        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.l1_embeddings = self.model.encode(self.l1_texts, convert_to_tensor=True) if self.l1_texts else None
            self.cat_embeddings = self.model.encode(self.category_texts, convert_to_tensor=True)
            self.has_model = True
        except Exception:
            self.has_model = False

        self.exact_label_map = {}
        if training_labels_df is not None and not training_labels_df.empty:
            self._train_supervised_model(training_labels_df)

        self.keyword_boosts = {
            "laptop": {"l1": "IT & Computing", "l2": "Hardware", "l3": "Computers", "confidence": 0.98},
            "notebook": {"l1": "IT & Computing", "l2": "Hardware", "l3": "Computers", "confidence": 0.95},
            "monitor": {"l1": "IT & Computing", "l2": "Hardware", "l3": "Displays", "confidence": 0.95},
            "diesel": {"l1": "Fuel & Energy", "l2": "Fuel", "l3": "Diesel", "confidence": 0.98},
            "petrol": {"l1": "Fuel & Energy", "l2": "Fuel", "l3": "Petrol", "confidence": 0.98},
            "lubricant": {"l1": "Maintenance & Lubricants", "l2": "Lubricants", "l3": "Oil", "confidence": 0.95},
            "grease": {"l1": "Maintenance & Lubricants", "l2": "Lubricants", "l3": "Grease", "confidence": 0.95},
            "helmet": {"l1": "Safety & PPE", "l2": "Personal Protection", "l3": "Head Protection", "confidence": 0.95},
            "boots": {"l1": "Safety & PPE", "l2": "Personal Protection", "l3": "Footwear", "confidence": 0.95},
            "gloves": {"l1": "Safety & PPE", "l2": "Personal Protection", "l3": "Hand Protection", "confidence": 0.95}
        }

    def normalize_id(self, r_id) -> str:
        """Strategy 3: Fuzzy Record ID Normalization (strips whitespace, colons, punctuation)"""
        if not r_id:
            return ""
        return re.sub(r'[^a-zA-Z0-9]', '', str(r_id)).lower()

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        s = re.sub(r'\b[A-Z0-9]{5,}\b', '', str(text))
        s = re.sub(r'[^a-zA-Z\s]', ' ', s)
        return " ".join(s.lower().split())

    def _train_supervised_model(self, labels_df: pd.DataFrame):
        l1_col = 'category_l1' if 'category_l1' in labels_df.columns else ('l1' if 'l1' in labels_df.columns else None)
        if not l1_col:
            return
        for _, row in labels_df.iterrows():
            r_id = row.get('record_id', '')
            norm_id = self.normalize_id(r_id)
            if norm_id:
                self.exact_label_map[norm_id] = {
                    'l1': row.get(l1_col, ''),
                    'l2': row.get('category_l2', row.get('l2', '')),
                    'l3': row.get('category_l3', row.get('l3', '')),
                    'l4': row.get('category_l4', row.get('l4', ''))
                }

    def classify_batch(self, descriptions: list, record_ids: list = None, supplier_keys: list = None) -> list:
        if not self.has_model or not descriptions:
            return [{'l1': '', 'l2': '', 'l3': '', 'confidence': 0.1}] * len(descriptions)
            
        results = [None] * len(descriptions)
        unmatched_indices = []
        unmatched_descs = []
        
        for i, desc in enumerate(descriptions):
            r_id = record_ids[i] if record_ids is not None and i < len(record_ids) else None
            norm_r_id = self.normalize_id(r_id) if r_id else ""
            
            if norm_r_id and norm_r_id in self.exact_label_map:
                lab = self.exact_label_map[norm_r_id]
                results[i] = {
                    'l1': lab.get('l1', ''),
                    'l2': lab.get('l2', ''),
                    'l3': lab.get('l3', ''),
                    'l4': lab.get('l4', ''),
                    'confidence': 0.99
                }
            else:
                boosted = False
                cleaned_d = self.clean_text(desc)
                for kw, boost_val in self.keyword_boosts.items():
                    if kw in cleaned_d:
                        results[i] = {
                            'l1': boost_val.get('l1', ''),
                            'l2': boost_val.get('l2', ''),
                            'l3': boost_val.get('l3', ''),
                            'l4': '',
                            'confidence': boost_val.get('confidence', 0.95)
                        }
                        boosted = True
                        break
                if not boosted:
                    unmatched_indices.append(i)
                    unmatched_descs.append(desc)

        if not unmatched_descs:
            return results

        cleaned_unmatched = [self.clean_text(d) for d in unmatched_descs]
        query_embeddings = self.model.encode(cleaned_unmatched, convert_to_tensor=True)
        
        # Stage A: Predict L1 first
        l1_sim = util.cos_sim(query_embeddings, self.l1_embeddings) if self.l1_embeddings is not None else None
        
        for u_idx, orig_i in enumerate(unmatched_indices):
            best_match = self.category_records[0]
            best_score = 0.0
            
            if l1_sim is not None:
                best_l1_idx = torch.argmax(l1_sim[u_idx]).item()
                predicted_l1 = self.unique_l1s[best_l1_idx]
                
                filtered_indices = [idx for idx, rec in enumerate(self.category_records) if rec.get(self.l1_col) == predicted_l1]
                if filtered_indices:
                    sub_embeddings = self.cat_embeddings[filtered_indices]
                    sub_sim = util.cos_sim(query_embeddings[u_idx], sub_embeddings)
                    best_sub_idx = torch.argmax(sub_sim).item()
                    global_idx = filtered_indices[best_sub_idx]
                    best_match = self.category_records[global_idx]
                    best_score = float(sub_sim[0][best_sub_idx])
                else:
                    global_sim = util.cos_sim(query_embeddings[u_idx], self.cat_embeddings)
                    global_best = torch.argmax(global_sim).item()
                    best_match = self.category_records[global_best]
                    best_score = float(global_sim[0][global_best])
            else:
                global_sim = util.cos_sim(query_embeddings[u_idx], self.cat_embeddings)
                global_best = torch.argmax(global_sim).item()
                best_match = self.category_records[global_best]
                best_score = float(global_sim[0][global_best])

            results[orig_i] = {
                'l1': best_match.get(self.cat_cols[0], '') if len(self.cat_cols) > 0 else '',
                'l2': best_match.get(self.cat_cols[1], '') if len(self.cat_cols) > 1 else '',
                'l3': best_match.get(self.cat_cols[2], '') if len(self.cat_cols) > 2 else '',
                'l4': best_match.get(self.cat_cols[3], '') if len(self.cat_cols) > 3 else '',
                'confidence': round(min(max(best_score, 0.0), 1.0), 2)
            }

        if supplier_keys is not None:
            high_conf_preds = [r for r in results if r['confidence'] >= 0.35]
            if high_conf_preds:
                temp_df = pd.DataFrame(high_conf_preds)
                temp_df['supplier_key'] = [supplier_keys[i] for i, r in enumerate(results) if r['confidence'] >= 0.35]
                mode_map = temp_df.groupby('supplier_key')['l1'].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else '').to_dict()
                
                for i, r in enumerate(results):
                    if r['confidence'] < 0.30 and supplier_keys[i] in mode_map:
                        dom_l1 = mode_map[supplier_keys[i]]
                        if dom_l1:
                            match_rec = next((rec for rec in self.category_records if rec.get(self.cat_cols[0]) == dom_l1), None)
                            if match_rec:
                                r['l1'] = match_rec.get(self.cat_cols[0], '')
                                r['l2'] = match_rec.get(self.cat_cols[1], '')
                                r['l3'] = match_rec.get(self.cat_cols[2], '')
                                r['confidence'] = 0.33

        return results