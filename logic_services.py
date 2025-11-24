import os
import re
import math
from collections import Counter
from datetime import datetime

# ==========================================
# 1. VEKTÖR ARAMA MOTORU (VECTOR SEARCH ENGINE)
# ==========================================
class VectorDatabase:
    def __init__(self, docs_path="legal_docs/mevzuat.txt"):
        self.docs = []
        self.load_documents(docs_path)

    def load_documents(self, path):
        """TXT dosyasından kanunları okur ve Akıllı Ayrıştırıcı ile böler."""
        if not os.path.exists(path):
            return
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # --- AKILLI AYRIŞTIRMA MANTIĞI ---
        # 1. Eğer dosyada '---' ayıracı varsa onu kullan
        if '---' in content:
            raw_docs = content.split('---')
        else:
            # 2. Ayıraç yoksa, "id:" ile başlayan satırları yeni belge başlangıcı kabul et
            # Regex ile her "id:" öncesine sanal bir ayıraç ekliyoruz
            # (?m) multiline mod, ^ satır başı demek
            content = re.sub(r'(?m)^id:', r'---id:', content)
            raw_docs = content.split('---')
        
        for raw in raw_docs:
            if not raw.strip(): continue
            
            doc = {}
            for line in raw.strip().split("\n"):
                line = line.strip()
                if not line: continue
                
                # İlk ':' işaretinden böl (Metin içinde : olabilir)
                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip()
                        doc[key] = val
            
            # İçerik alanı doluysa listeye ekle
            if "icerik" in doc:
                self.docs.append(doc)

    def text_to_vector(self, text):
        """Metni matematiksel vektöre çevirir (Bag of Words)."""
        words = re.findall(r'\w+', text.lower())
        return Counter(words)

    def get_cosine_similarity(self, vec1, vec2):
        """İki vektör arasındaki açıyı (benzerliği) hesaplar."""
        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator: return 0.0
        return float(numerator) / denominator

    def search(self, query, category_filter=None):
        """Kullanıcı sorgusuna en uygun kanunu bulur."""
        query_vec = self.text_to_vector(query)
        results = []

        for doc in self.docs:
            # Kategori filtresi
            if category_filter and category_filter != doc.get("kategori"):
                continue
            
            # Başlık ve içeriği birleştirip vektöre çevir
            doc_text = doc["icerik"] + " " + doc.get("baslik", "")
            doc_vec = self.text_to_vector(doc_text)
            
            score = self.get_cosine_similarity(query_vec, doc_vec)
            
            # Hassasiyet eşiği
            if score > 0.05: 
                results.append((score, doc))

        # Puana göre sırala
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]

# Global Vektör Veritabanı Örneği
vector_db = VectorDatabase()

def search_legal_docs(query, category):
    """App.py tarafından çağrılan ana arama fonksiyonu."""
    if len(query) < 3: return "" # Çok kısa sorguları yoksay
    
    results = vector_db.search(query, category)
    
    if not results:
        return "Özel bir mevzuat eşleşmesi bulunamadı, genel hukuk kuralları uygulanacaktır."
    
    # En iyi sonucu döndür
    best_doc = results[0]
    return f"KANUN: {best_doc.get('baslik')}\nİÇERİK: {best_doc.get('icerik')}"

# ==========================================
# 2. DETERMINISTIK KURAL MOTORU (RULE ENGINE)
# ==========================================
def check_rules(category, text, ocr_text=""):
    warnings = []
    combined_text = (text + " " + ocr_text).lower()

    # KURAL 1: Tüketici Parasal Sınır
    if category == "tuketici_haklari":
        prices = re.findall(r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:tl|türk lirası)', combined_text)
        for p in prices:
            try:
                clean_price = float(p.replace('.', '').replace(',', '.'))
                if clean_price > 104000:
                    warnings.append(f"⚠️ DİKKAT (Rule-Engine): Tespit edilen tutar ({clean_price} TL), 2024 yılı sınırını (104.000 TL) aşmaktadır. Tüketici Mahkemesi'ne başvurulmalı.")
            except: pass

    # KURAL 2: Trafik Cezası Süre
    if category == "trafik_cezasi":
        dates = re.findall(r'(\d{2}[./-]\d{2}[./-]\d{4})', combined_text)
        today = datetime.now()
        for d in dates:
            try:
                event_date = datetime.strptime(d.replace('/', '.').replace('-', '.'), '%d.%m.%Y')
                delta = (today - event_date).days
                if 15 < delta < 365: 
                    warnings.append(f"⚠️ KRİTİK UYARI (Rule-Engine): Tarih ({d}) üzerinden {delta} gün geçmiştir. 15 günlük yasal itiraz süresi aşılmış olabilir.")
            except: pass

    if not warnings: return ""
    return "\n".join(warnings)