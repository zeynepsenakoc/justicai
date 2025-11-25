import os
import re
import json
import math
from collections import Counter
from datetime import datetime
from openai import OpenAI

# ==========================================
# 1. HİBRİT VEKTÖR ARAMA MOTORU (SEMANTIC RAG)
# ==========================================
class VectorDatabase:
    def __init__(self, docs_path="legal_docs/mevzuat.txt"):
        self.docs = []
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        # API Key varsa istemciyi başlat
        if self.api_key and not "benim keyim" in self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except: pass
            
        self.load_documents(docs_path)

    def load_documents(self, path):
        if not os.path.exists(path): return
        with open(path, "r", encoding="utf-8") as f: content = f.read()
        
        if '---' in content: raw_docs = content.split('---')
        else: content = re.sub(r'(?m)^id:', r'---id:', content); raw_docs = content.split('---')
        
        for raw in raw_docs:
            if not raw.strip(): continue
            doc = {}
            for line in raw.strip().split("\n"):
                line = line.strip()
                if not line: continue
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        doc[parts[0].strip()] = parts[1].strip()
            
            if "icerik" in doc:
                # Eğer API aktifse, dökümanı yüklerken vektörünü de oluştur (Caching)
                # Not: Gerçek prodüksiyonda bu vektörler veritabanında saklanır.
                # Burada demo amaçlı her açılışta (hafızada) oluşturuyoruz.
                if self.client:
                    doc["vector"] = self.get_embedding(doc["icerik"] + " " + doc.get("baslik", ""))
                self.docs.append(doc)

    def get_embedding(self, text):
        """Metni OpenAI kullanarak semantik vektöre çevirir."""
        try:
            if not self.client: return None
            text = text.replace("\n", " ")
            return self.client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
        except:
            return None

    def cosine_similarity(self, v1, v2):
        """İki liste (vektör) arasındaki benzerliği hesaplar."""
        dot_product = sum(a*b for a, b in zip(v1, v2))
        magnitude1 = math.sqrt(sum(a*a for a in v1))
        magnitude2 = math.sqrt(sum(b*b for b in v2))
        if not magnitude1 or not magnitude2: return 0.0
        return dot_product / (magnitude1 * magnitude2)

    # --- ESKİ USUL (FALLBACK) ---
    def text_to_counter(self, text):
        words = re.findall(r'\w+', text.lower())
        return Counter(words)

    def counter_cosine_similarity(self, vec1, vec2):
        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])
        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)
        return float(numerator) / denominator if denominator else 0.0

    def search(self, query, category_filter=None):
        # 1. YÖNTEM: SEMANTİK ARAMA (OpenAI Vektörleri)
        if self.client:
            query_vec = self.get_embedding(query)
            if query_vec:
                results = []
                for doc in self.docs:
                    if category_filter and category_filter != doc.get("kategori"): continue
                    if "vector" in doc:
                        score = self.cosine_similarity(query_vec, doc["vector"])
                        if score > 0.25: results.append((score, doc))
                results.sort(key=lambda x: x[0], reverse=True)
                return [r[1] for r in results]

        # 2. YÖNTEM: ESKİ USUL (API Yoksa Yedek Sistem)
        query_cnt = self.text_to_counter(query)
        results = []
        for doc in self.docs:
            if category_filter and category_filter != doc.get("kategori"): continue
            doc_text = doc["icerik"] + " " + doc.get("baslik", "")
            score = self.counter_cosine_similarity(query_cnt, self.text_to_counter(doc_text))
            if score > 0.05: results.append((score, doc))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]

# Global Veritabanını Başlat
vector_db = VectorDatabase()

def search_legal_docs(query, category):
    if len(query) < 3: return ""
    results = vector_db.search(query, category)
    if not results: return "Özel bir mevzuat eşleşmesi bulunamadı."
    best = results[0]
    return f"KANUN: {best.get('baslik')}\nİÇERİK: {best.get('icerik')}"

# ==========================================
# 2. UZMAN KURAL MOTORU (RULE ENGINE)
# ==========================================
class RuleEngine:
    def __init__(self, rules_path="legal_docs/rules.json"):
        self.rules = {}
        self.load_rules(rules_path)
    
    def load_rules(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try: self.rules = json.load(f)
                except: pass

    def check(self, category, text, ocr_text=""):
        warnings = []
        text = (text + " " + ocr_text).lower()
        cat_rules = self.rules.get(category, {})
        if not cat_rules: return ""

        # A) Parasal Sınır
        if "parasal_sinir" in cat_rules:
            rule = cat_rules["parasal_sinir"]
            limit = rule.get("2025_limit_ilce", rule.get("limit", 0))
            msg = rule.get("uyari_mesaji", "")
            amounts = re.findall(r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:tl|türk lirası)', text)
            for amt in amounts:
                try:
                    val = float(amt.replace('.', '').replace(',', '.'))
                    if val > limit: warnings.append(msg.format(deger=val, limit_ilce=limit))
                except: pass

        # B) Tarih Kontrolleri
        time_rules = ["itiraz_suresi", "cayma_hakki", "ise_iade", "savcilik_sikayet", "ayipli_mal"]
        for key in time_rules:
            if key in cat_rules:
                rule = cat_rules[key]
                limit = rule.get("gun") or rule.get("sure_gun") or (rule.get("zaman_asimi_ay", 0)*30) or (rule.get("zaman_asimi_yil", 0)*365)
                msg = rule.get("uyari_mesaji", "")
                if limit > 0:
                    dates = re.findall(r'(\d{2}[./-]\d{2}[./-]\d{4})', text)
                    for d in dates:
                        try:
                            dt = datetime.strptime(d.replace('/', '.').replace('-', '.'), '%d.%m.%Y')
                            diff = (datetime.now() - dt).days
                            if 0 < diff > limit and diff < (365*5):
                                try: warnings.append(msg.format(fark_gun=diff, fark_ay=round(diff/30, 1), fark_yil=round(diff/365, 1)))
                                except: warnings.append(msg)
                        except: pass

        # C) Eksik Belge
        if "zorunlu_kelimeler" in cat_rules:
            if not any(k in text for k in cat_rules["zorunlu_kelimeler"]):
                warnings.append(cat_rules.get("eksik_belge_mesaji", ""))
        
        # D) Özel Durumlar
        if category == "kira" and "kira_artisi" in cat_rules and ("zam" in text or "artış" in text):
            warnings.append(cat_rules["kira_artisi"].get("uyari_mesaji", "").format(oran="71.5"))
        
        if category == "bilişim_suclari" and "url_tespiti" in cat_rules and "http" not in text:
            warnings.append(cat_rules["url_tespiti"].get("uyari_mesaji", "").format(url_var_mi="URL"))

        return "\n".join(warnings)

expert_system = RuleEngine()

def check_rules(category, text, ocr_text=""):
    return expert_system.check(category, text, ocr_text)