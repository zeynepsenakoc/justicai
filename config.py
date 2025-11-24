import os
import json

# ===========================================================
# 1) LLM ANA PROMPT — "AVUKAT & SORGUCU MODU"
# ===========================================================

BASE_PROMPT = """
Sen uzman bir Türk Hukuku avukatısın. İki modun var:

MOD 1: SORGU HÂKİMİ (Eksik Bilgi Varsa)
Kullanıcının verdiği bilgiler (veya OCR verisi) dilekçe yazmak için yetersizse (Tarih, Tutar, Olayın Özeti, Karşı Taraf Bilgisi eksikse), ASLA dilekçe yazma.
Bunun yerine, eksik olan bilgileri kibar ve resmi bir dille sor.
JSON Çıktısı: "status": "SORGU", "questions": ["Soru 1", "Soru 2"]

MOD 2: DİLEKÇE YAZARI (Bilgiler Tamsa)
Tüm kritik bilgiler mevcutsa, verilen Kanun Maddelerini (RAG) ve Sistem Uyarılarını (Rules) dikkate alarak resmi bir dilekçe yaz.
JSON Çıktısı: "status": "DILEKCE_HAZIR", "hitap_makam": "...", "dilekce_metni": "...", "hukuki_oneriler": "..."

BAĞLAM VERİLERİ:
{context_data}

ÇIKTI FORMATI (SADECE JSON):
Eğer bilgi eksikse:
{{ "status": "SORGU", "questions": ["...", "..."] }}

Eğer bilgi tamsa:
{{ "status": "DILEKCE_HAZIR", "hitap_makam": "...", "dilekce_metni": "...", "hukuki_oneriler": "..." }}
"""

# ===========================================================
# 2) KATEGORİLER
# ===========================================================
CATEGORIES = {
    "trafik_cezasi": {
        "title": "Trafik Cezası İtirazı",
        "law": "2918 Sayılı KTK",
        "required_fields": ["plaka", "ceza tarihi", "tebligat tarihi"]
    },
    "tuketici_haklari": {
        "title": "Tüketici Hakları Başvurusu",
        "law": "6502 Sayılı Kanun",
        "required_fields": ["ürün", "satıcı", "tarih", "sorun"]
    },
    "kira": {
        "title": "Kira Hukuku",
        "law": "TBK",
        "required_fields": []
    },
    "is_hukuku": {
        "title": "İş Hukuku",
        "law": "İş Kanunu",
        "required_fields": []
    },
    "sosyal_medya": {
        "title": "Bilişim Suçları",
        "law": "TCK",
        "required_fields": []
    },
    "dolandiricilik": {
        "title": "Dolandırıcılık",
        "law": "TCK",
        "required_fields": []
    },
    "bankacilik": {
        "title": "Bankacılık",
        "law": "Bankacılık Kanunu",
        "required_fields": []
    },
    "kargo": {
        "title": "Kargo Tazmin",
        "law": "TTK",
        "required_fields": []
    }
}

# ===========================================================
# 3) PDF HTML TEMPLATE (Çift Parantezli CSS)
# ===========================================================
PETITION_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; margin: 40px; }}
h2 {{ text-align: center; margin-bottom: 20px; text-transform: uppercase; }}
.section {{ margin-top: 35px; white-space: pre-wrap; text-align: justify; }}
.footer {{ margin-top: 60px; text-align: right; }}
.oneriler {{ background: #fff3cd; padding: 20px; border: 1px solid #ffeeba; margin-top: 50px; page-break-before: always; }}
</style>
</head>
<body>
<h2>{hitap_makam}</h2>
<div class="section">{dilekce_metni}</div>
<div class="footer">
<p><strong>Tarih:</strong> {tarih}</p>
<p><strong>Ad Soyad:</strong> {ad_soyad}</p>
<p style="margin-top:30px;"><strong>İmza:</strong></p>
<br><br>
</div>
<div class="oneriler">
<h3><i class="fas fa-lightbulb"></i> Hukuki Tavsiyeler</h3>
<hr>
{hukuki_oneriler}
</div>
</body>
</html>
"""