import os
import re
import json
import logging
import chromadb
import threading
import math
from datetime import datetime
from chromadb.utils import embedding_functions


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class LegalVectorDB:
    _lock = threading.Lock()
    def __init__(self, docs_path="legal_docs/mevzuat.txt", db_path="./chroma_db"):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.docs_path = docs_path
        
        if self.api_key:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.api_key,
                model_name="text-embedding-3-small"
            )
        else:
            logger.warning("⚠️ OpenAI API Key bulunamadı! Varsayılan embedding kullanılıyor.")
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self.client = chromadb.PersistentClient(path=db_path)
        
        self.collection = self.client.get_or_create_collection(
            name="legal_knowledge_base",
            embedding_function=self.embedding_fn
        )

        self._init_db()

    def _parse_documents(self):
        if not os.path.exists(self.docs_path):
            return []

        with open(self.docs_path, "r", encoding="utf-8") as f:
            content = f.read()

        if '---' in content:
            raw_docs = content.split('---')
        else:
            content = re.sub(r'(?m)^id:', r'---id:', content)
            raw_docs = content.split('---')

        parsed_docs = []
        for raw in raw_docs:
            if not raw.strip(): continue
            doc = {}
            lines = raw.strip().split("\n")
            for line in lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    doc[key.strip()] = val.strip()
            
            if "id" in doc and "icerik" in doc:
                parsed_docs.append({
                    "id": doc["id"],
                    "document": f"{doc.get('baslik', '')} \n {doc.get('icerik', '')}",
                    "metadata": {
                        "baslik": doc.get("baslik", "Kanun Maddesi"),
                        "kategori": doc.get("kategori", "genel"),
                        "icerik_preview": doc.get("icerik", "")[:300]
                    }
                })
        return parsed_docs

    def _init_db(self):
        if self.collection.count() > 0:
            return

        logger.info("♻️ ChromaDB ilk kez oluşturuluyor, veriler işleniyor...")
        docs = self._parse_documents()
        
        if not docs: return

        ids = [d["id"] for d in docs]
        documents = [d["document"] for d in docs]
        metadatas = [d["metadata"] for d in docs]

        try:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"✅ Başarıyla {len(docs)} belge vektörleştirildi ve kaydedildi.")
        except Exception as e:
            logger.error(f"❌ Veri yükleme hatası: {e}")

    def search(self, query, category_filter=None, n_results=3):
        """
        Thread-Safe (Güvenli) Arama Fonksiyonu
        ✅ DÜZELTME: Kategori filtresi esnek hale getirildi
        """
        try:
            
            normalized_category = None
            if category_filter:
                
                normalized_category = category_filter.split("_")[0]
            

            enhanced_query = query
            if normalized_category:
                enhanced_query = f"{normalized_category} {query}"
            

            with self._lock:
                results = self.collection.query(
                    query_texts=[enhanced_query],
                    n_results=n_results
                    
                )

        
            formatted_results = []
            if results["ids"]:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "baslik": results["metadatas"][0][i]["baslik"],
                        "icerik": results["metadatas"][0][i]["icerik_preview"],
                        "kategori": results["metadatas"][0][i].get("kategori", "genel")
                    })
            return formatted_results
            
        except Exception as e:
            logger.error(f"Arama hatası: {e}")
            return []

vector_db = LegalVectorDB()


FALLBACK_LAWS = {
 
    "egitim": """
YÖK Yükseköğretim Kurumları Öğrenci Disiplin Yönetmeliği (2012):
- Madde 7: Sınav sonuçlarına itiraz hakkı düzenlenmiştir. Öğrenci, notunu öğrendiği tarihten itibaren 5 iş günü içinde dekanlığa başvurabilir.
- Madde 8: İtiraz üzerine sınav kağıdı tekrar değerlendirilir. Maddi hata (toplama hatası, soru değerlendirme hatası) tespit edilmesi halinde düzeltme yapılır.
- Not düzeltme talebi: Öğrenci numarası, ders kodu, sınav türü (vize/final) ve itiraz gerekçesi belirtilmelidir.

YÖK Lisans Eğitim-Öğretim Yönetmeliği:
- Kayıt dondurma: Sağlık, maddi imkansızlık veya zorunlu haller nedeniyle kayıt dondurulabilir (Max. 2 yarıyıl).
- Üstten ders alma: GNO 2.50 üzeri öğrenciler izin alarak üst dönem derslerini alabilir.
""",
    
  
    "banka": """
5464 Sayılı Banka Kartları ve Kredi Kartları Kanunu:
- Madde 4: Kart hamili, kartının yetkisiz kullanımını öğrendiği anda kartı bloke ettirebilir.
- Madde 13: Hatalı/yetkisiz işlemler için kart hamili, işlem tarihinden itibaren 15 gün içinde bankaya yazılı itiraz edebilir.
- Chargeback (Ters İbraz): Banka, itiraz üzerine tüccara soruşturma başlatır. İşlem iptal edilir ve hesaba iade yapılır.

BDDK Tüketici İşlemleri Yönetmeliği:
- Kredi yapılandırma: Ödeme güçlüğü yaşayan müşteriler, vade uzatma veya taksitlendirme talep edebilir.
- Hesap blokesi: MASAK veya yasal kararlar dışındaki blokeler, gerekçe gösterilmeksizin kaldırılamaz.
""",
   
    "belediye": """
5393 Sayılı Belediye Kanunu:
- Madde 14: Hemşerilerin belediye hizmetlerinden eşit ve kaliteli şekilde yararlanma hakkı vardır.
- Madde 75: Yol, su, kanalizasyon, aydınlatma gibi altyapı hizmetlerinden kaynaklanan sorunlar için belediye sorumludur.
- Şikayet hakkı: Hemşeriler, hizmet aksamalarını dilekçe ile belediye başkanlığına bildirebilir.

İmar Kanunu (3194):
- İmar durumu belgesi: Ada/parsel bilgisi ile başvurulur. Taşınmazın imar planındaki konumunu gösterir.
- Ruhsatsız yapı: Belediye, ruhsatsız yapıları tespit eder ve yıkım kararı alabilir.
""",
    
    
    "aile": """
Türk Medeni Kanunu (TMK) - Aile Hukuku:
- Madde 166: Anlaşmalı boşanma için evlilik en az 1 yıl sürmüş olmalıdır.
- Madde 166/3: Taraflar, nafaka, tazminat, mal paylaşımı konusunda anlaşmışlarsa mahkeme boşanmaya karar verir.
- Madde 174-176: Tedbir nafakası, yoksulluk nafakası, iştirak nafakası düzenlenmiştir.
- Madde 182: Velayetin düzenlenmesi - Çocuğun yüksek yararı esas alınır.
""",
    
    "kira": """
Türk Borçlar Kanunu (TBK) - Kira Hukuku:
- Madde 315: Kiracının kira borcunu ödememesi (temerrüt) nedeniyle tahliye: 2 aylık gecikme şarttır.
- Madde 350: Gereksinim (ihtiyaç) nedeniyle tahliye: Kiraya veren, kendisi/çocukları için gereksinim ispatlamalıdır.
- Madde 344: 5 yıl üzeri kiralarda, kira bedeli piyasa koşullarına uyarlanabilir.
- Madde 138: Aşırı ifa güçlüğü (Rebus Sic Stantibus): Ekonomik kriz, deprem gibi olağanüstü durumlarda sözleşme değiştirilebilir.
""",
    
    "is": """
4857 Sayılı İş Kanunu:
- Madde 18-21: İşe İade Davası - İşverenin geçerli sebep göstermeden fesih yapması halinde açılır. 30 gün içinde başvuru zorunludur.
- Kıdem Tazminatı: 1 yıl üzeri çalışan işçiye, haksız fesih durumunda 30 günlük brüt ücret x çalışma yılı ödenir.
- Fazla Mesai: Haftalık 45 saati aşan çalışmalar %50 zamlı ücretle ödenir.
- Madde 24/II: Mobbing (psikolojik taciz) nedeniyle işçi haklı fesih yapabilir ve tazminat talep edebilir.
""",
    
    "icra": """
İcra ve İflas Kanunu (İİK):
- Madde 62: İcra takibine itiraz - Borçlu, takip tarihinden itibaren 7 gün içinde itiraz edebilir.
- Madde 72: Menfi Tespit Davası - Borcu olmadığını iddia eden borçlu, 1 yıl içinde dava açar.
- İtiraz türleri: Borca itiraz (borç yok), imzaya itiraz (belge sahte), şekle itiraz (takip usulsüz).
""",
    
    "ceza": """
Ceza Muhakemesi Kanunu (CMK):
- Madde 158: Suç duyurusu - Her vatandaş, bir suçu öğrendiğinde Cumhuriyet Savcılığına bildirebilir.
- Suç tarifi: Olay yeri, tarih, şüpheli bilgisi, deliller (varsa) belirtilmelidir.
- Şikayet süresi: Takibi şikayete bağlı suçlarda (hakaret, tehdit vb.) 6 ay içinde şikayet zorunludur.
""",
    
  
    "tuketici": """
6502 Sayılı Tüketicinin Korunması Hakkında Kanun:
- Madde 11: Ayıplı Mal - Tüketici, satın aldığı malda ayıp tespit ederse; ücretsiz onarım, bedel indirimi, ayıpsız misli ile değiştirme veya sözleşmeden dönme haklarına sahiptir.
- Madde 13-16: Ayıplı Hizmet - İnternet, tatil paketi, tamirat gibi hizmetlerde kusur olması halinde benzer haklar tanınır.
- Madde 82: Tüketici Hakem Heyeti - Uyuşmazlık bedeli, 2025 yılı için ilçe hakem heyetlerinde 85.000 TL'ye kadardır.
- Cayma Hakkı (Madde 48): Mesafeli satışlarda (internet, telefon) 14 gün içinde cayma hakkı vardır.
""",
    

    "trafik": """
Karayolları Trafik Kanunu (KTK):
- Trafik Cezası İptali: İdari para cezasına karşı tebliğ tarihinden itibaren 15 gün içinde sulh ceza hakimliğine itiraz edilebilir.
- Araç Değer Kaybı: Kaza sonrası araç değer kaybı, Sigorta Genel Şartları'na göre tazminat olarak talep edilebilir (ekspertiz raporu gerekli).
""",
    

    "kurum": """
Abonelik Sözleşmeleri Yönetmeliği:
- Madde 23: Tüketici, abonelik sözleşmesini her zaman feshedebilir. Taahhütlü sözleşmelerde cayma tazminatı (kalan süre x aylık bedel) talep edilebilir.
- Fatura İtirazı: Yüksek veya hatalı faturalara karşı, fatura tarihinden itibaren 30 gün içinde kurum müşteri hizmetlerine yazılı itiraz yapılmalıdır.
"""
}

def search_legal_docs(query, category=None):
    """
    ✅ DÜZELTME 4: Mevzuat arama fonksiyonu - fallback mekanizmalı
    """
    if len(query) < 3: 
        return "Sorgu çok kısa."

    results = vector_db.search(query, category_filter=category)
    
    
    if not results or len(results) < 2:
        logger.warning(f"⚠️ VectorDB'de yeterli sonuç yok (kategori: {category}), fallback mevzuat kullanılıyor...")
        
       
        normalized_cat = category.split("_")[0] if category else "genel"
        
       
        fallback_text = FALLBACK_LAWS.get(normalized_cat, FALLBACK_LAWS.get("tuketici", "Genel hükümler uygulanır."))
        
        return f"""
⚖️ MEVZUAT TARAMASI (Fallback Modu - VectorDB Boş)
{'═' * 60}

{fallback_text}

ℹ️ NOT: Bu mevzuat bilgileri sistem varsayılanlarıdır. Güncel yönetmelikler için YÖK/Bakanlık sitelerini kontrol ediniz.
"""
    

    context = "⚖️ MEVZUAT TARAMASI (ChromaDB Semantic Search)\n" + "═" * 60 + "\n"
    for i, doc in enumerate(results, 1):
        context += f"{i}. {doc.get('baslik', 'Kanun')}\n"
        context += f"   Kategori: {doc.get('kategori', 'Genel')}\n"
        context += f"   İÇERİK: {doc.get('icerik', 'N/A')}...\n\n"
    
    return context


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
        full_text = (text + " " + ocr_text).lower()
        cat_rules = self.rules.get(category, {})
        
        if not cat_rules: return ""

        if "parasal_sinir" in cat_rules:
            rule = cat_rules["parasal_sinir"]
            limit = rule.get("2025_limit_ilce", 0)
            msg = rule.get("uyari_mesaji", "")
            
            amounts = re.findall(r'(\d{1,3}(?:[.,]\d{3})*)\s*(?:tl|türk lirası)', full_text)
            for amt in amounts:
                try:
                    val = float(amt.replace('.', '').replace(',', '.'))
                    if val > limit:
                        warnings.append(msg.format(dever=val, limit_ilce=limit))
                except: pass

        if "zorunlu_kelimeler" in cat_rules:
            missing_docs = True
            for k in cat_rules["zorunlu_kelimeler"]:
                if k in full_text:
                    missing_docs = False
                    break
            if missing_docs:
                warnings.append(cat_rules.get("eksik_belge_mesaji", ""))

        dates = re.findall(r'(\d{2}[./-]\d{2}[./-]\d{4})', full_text)
        if dates:
            time_rule = None
            for key in ["itiraz_suresi", "cayma_hakki", "ise_iade", "ayipli_mal"]:
                if key in cat_rules:
                    time_rule = cat_rules[key]
                    break
            
            if time_rule:
                limit_days = time_rule.get("gun") or time_rule.get("sure_gun") or (time_rule.get("zaman_asimi_yil", 0)*365)
                msg = time_rule.get("uyari_mesaji", "")
                for d_str in dates:
                    try:
                        dt = datetime.strptime(d_str.replace('/', '.').replace('-', '.'), '%d.%m.%Y')
                        diff = (datetime.now() - dt).days
                        if diff > limit_days and diff < (365*10):
                            warnings.append(msg.format(fark_gun=diff))
                    except: pass

        return "\n".join(warnings)

expert_system = RuleEngine()

def check_rules(category, text, ocr_text=""):
    warnings = expert_system.check(category, text, ocr_text)
    if not warnings: return ""
    return "\n⚠️ HUKUKİ RİSK ANALİZİ (Rule Engine v2.0)\n" + "═" * 45 + "\n" + warnings



class EthicsEngine:
    def __init__(self):
   
        self.risk_categories = {
            "finansal_suc": [
                r"sahte\s+fatura", r"naylon\s+fatura", r"vergi\s+ka[çc]ırma", 
                r"kara\s+para", r"rüşvet", r"zimmet", r"hayali\s+ihracat"
            ],
            "siber_suc": [
                r"hackle", r"ddos", r"hesap\s+[çc]al", r"şifre\s+kır", 
                r"virüs\s+yaz", r"trojan", r"casus\s+yazılım"
            ],
            "illegal_ticaret": [
                r"uyuşturucu", r"torbacı", r"kaçakçılık", r"silah\s+satış", 
                r"bomba\s+yapım", r"patlayıcı"
            ],
            "adli_suistimal": [
                r"delil\s+karart", r"yalan\s+beyan", r"hakime\s+rüşvet", 
                r"sahte\s+şahit", r"sahte\s+belge\s+düzenle"
            ]
        }

        
        self.violence_roots = ["döv", "öldür", "yarala", "tehdit", "bıçak", "silah", "vur", "darp"]

     
        self.victim_indicators = [
            "tarafından", "maruz kaldım", "şikayetçiyim", "mağdurum", 
            "darp raporu", "tehdit ediliyorum", "saldırıya uğradım", 
            "bıçaklandım", "dövüldüm", "vuruldum", "yaralandım",
            "başvur", "başvuru", "başvurmak"
        ]

    def analyze(self, text):
        text_lower = text.lower()


        for category, patterns in self.risk_categories.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return False, f"Tespit edilen içerik ({category.upper().replace('_', ' ')}) güvenlik politikalarımıza aykırıdır."

       
        is_victim = any(ind in text_lower for ind in self.victim_indicators)
        if is_victim:
            return True, "Güvenli (Mağduriyet/Hukuki İşlem Tespiti)"

       
        for root in self.violence_roots:
            risky_patterns = [
                f"nasıl {root}", 
                f"{root}.*?rım",   
                f"{root}.*?cam",   
                f"{root}.*?cağım", 
                f"{root}.*?cem",   
                f"{root}.*?mak istiyorum" 
            ]
            
            for pattern in risky_patterns:
                if re.search(pattern, text_lower):
                    return False, f"Sistem, şiddet ({root}) veya yasa dışı eylem içeren talepleri işleme almaz."

        return True, "Güvenli"

ethics_guard = EthicsEngine()

class AdvancedSuccessPredictor:
    def __init__(self):
        self.evidence_matrix = {
            "tuketici": {
                "fatura": 25, "fiş": 20, "garanti belgesi": 15, 
                "servis raporu": 30, "yazışma": 10, "fotoğraf": 15
            },
            "kira": {
                "kira sözleşmesi": 35, "kontrat": 35, "banka dekontu": 25, 
                "ihtarname": 20, "tapu": 15, "tahliye taahhütnamesi": 40
            },
            "is": {
                "sgk dökümü": 25, "maaş bordrosu": 25, "fesih bildirimi": 20, 
                "ihtarname": 15, "iş sözleşmesi": 20, "tanık": 10
            },
            "genel": {
                "resmi belge": 15, "rapor": 15, "tutanak": 20, 
                "fotoğraf": 10, "video kaydı": 15, "tanık": 5
            }
        }
        
        self.uncertainty_patterns = [
            (r"bilmiyorum", -15), (r"emin değilim", -10), 
            (r"belgem yok", -20), (r"kaybettim", -15), 
            (r"hatırlamıyorum", -10), (r"kanıtım yok", -25), 
            (r"sözlü anlaşma", -20), (r"galiba", -5)
        ]

    def analyze_case(self, category, text, ocr_text=""):
        full_text = (text + " " + ocr_text).lower()
        current_score = 35.0 
        
        found_strong_evidence = []
        missing_critical_evidence = []
        detected_risks = []
        
        target_context = "genel"
        if "tuketici" in category: target_context = "tuketici"
        elif "kira" in category: target_context = "kira"
        elif "is" in category: target_context = "is"
        
        rules = self.evidence_matrix[target_context]
        
        for evidence, weight in rules.items():
            if re.search(rf"{evidence}(?!.*(yok|kayıp|bulamıyorum|olmadı))", full_text):
                current_score += weight
                found_strong_evidence.append(evidence.title())
            else:
                if weight >= 20: 
                    missing_critical_evidence.append(evidence.title())

        for pattern, penalty in self.uncertainty_patterns:
            if re.search(pattern, full_text):
                current_score += penalty
                detected_risks.append(f"Belirsiz İfade ({penalty} Puan)")

        word_count = len(full_text.split())
        if word_count > 100: current_score += 10
        elif word_count < 15: current_score -= 15

        final_score = int(min(98, max(5, current_score)))
        
        return {
            "score": final_score,
            "confidence": self._get_confidence_level(final_score),
            "advice": self._generate_strategic_advice(final_score, missing_critical_evidence, len(detected_risks)),
            "factors": found_strong_evidence[:5]
        }

    def _get_confidence_level(self, score):
        if score >= 85: return "Çok Yüksek (Kazanma İhtimali Güçlü)"
        if score >= 70: return "Yüksek (İspat Yükü Karşılanabilir)"
        if score >= 50: return "Orta (Ek Delil Gerekli)"
        if score >= 30: return "Düşük (Riskli Dava)"
        return "Kritik (Hukuki Yarar Yok)"

    def _generate_strategic_advice(self, score, missing, risk_count):
        advice = ""
        
        if score >= 80:
            advice = "Mevcut delil durumu, hukuki iddianızı ispatlamak için yeterli görünüyor. Dilekçeyi bu haliyle işleme koyabilirsiniz."
        elif score >= 50:
            missing_text = ", ".join(missing[:2]) if missing else "ek yazılı delil"
            advice = f"Davanızın temeli var ancak ispat gücünü artırmak için {missing_text} sunmanız kritik önem taşıyor."
        else:
            advice = "Mevcut anlatım ve deliller, mahkemede haklılığınızı ispatlamaya yetmeyebilir. Mutlaka bir avukattan profesyonel görüş alınız."
            
        if risk_count > 0:
            advice += " Ayrıca, olay örgüsündeki belirsiz ifadeler ('hatırlamıyorum' vb.) hakim nezdinde aleyhinize yorumlanabilir, netleştirin."
            
        return advice
        
success_predictor = AdvancedSuccessPredictor()