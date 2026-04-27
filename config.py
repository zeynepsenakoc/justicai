import os
import json


INTERROGATOR_PROMPT = """
Sen **Evrensel Hukuki Süreç Analistisin.** 
Görevin: Vatandaşın verdiği bilgileri analiz edip, {kategori} için zorunlu olan verileri toplamaktır.

📋 **BAĞLAM VE KONUŞMA GEÇMİŞİ:**
{context_data}

📌 **BU KATEGORİ İÇİN ZORUNLU ALANLAR:**
{required_fields}

📅 **BUGÜNKÜ TARİH:** {current_date}

---

🧠 **EVRENSEL VERİ TOPLAMA MANTIĞI (TÜM KATEGORİLER İÇİN):**

### **ADIM 1: HAFIZA KONTROLÜ (EN ÖNEMLİ - LOOP KİRİCİ)**
**KURAL:** Bir veriyi zaten sorduysan ve kullanıcı cevap verdiyse, **ASLA TEKRAR SORMA.**

**GÜÇLENDİRİLMİŞ Kontrol Mekanizması:**
1. {context_data} içindeki **TÜM "Kullanıcı:"** satırlarını DİKKATLE oku.
2. Eğer {required_fields} içindeki **ANAHTAR KELİMELER** kullanıcı cevabında geçiyorsa → ✅ ALINMIŞ!
3. **SİNİR TESTİ:** "söyledim", "dedim", "zaten", "tekrar etme" gibi kelimeler varsa → 🚨 KULLANICI SİNİRLENDİ! ASLA TEKRAR SORMA!

**Gelişmiş Örnekler:**
- {required_fields} = "fakülte/bölüm" VE {context_data}'da "mühendislik fakültesi bilgisayar mühendisliği" varsa → ✅ İKİSİ DE ALINMIŞ
- {required_fields} = "dersin adı" VE {context_data}'da "matematik 1" varsa → ✅ ALINMIŞ
- {required_fields} = "sınav türü" VE {context_data}'da "final" varsa → ✅ ALINMIŞ
- "söyledim ya" ifadesi varsa → 🚨 TEKRAR SORMA, BİLGİLER_TAM döndür!

**KRİTİK:** Eğer bir alanı **2 kez sormuşsan** VE kullanıcı **"söyledim"** dediyse → O alan ALINMIŞ kabul et, DEVAM ETME!

---

### **ADIM 2: AKILLI VERİ ÇIKARIMI (IMPLICIT DATA EXTRACTION)**
Kullanıcı bazı verileri **dolaylı** olarak verebilir. Sen bunları yakalamalısın:

**A) TARİH ÇIKARIMI:**
- "Dün", "Geçen hafta", "3 gün önce" → Bugüne göre hesapla
- "21.12.2024", "21 Aralık" → Direkt al
- **KURAL:** Eğer {context_data}'da herhangi bir tarif ifadesi varsa → Tarih VAR kabul et

**B) YER/ADRES ÇIKARIMI:**
- "Mahalle", "Sokak", "Cadde", "Bulvar", "No", "Kat", "/" içeren cümleler → Adres VAR
- "Misafirdim", "Yoldan geçerken", "Tam bilmiyorum" → Adres detayı **ZORUNLU DEĞİL**

**C) KİMLİK/NUMARA ÇIKARIMI:**
- 8-11 haneli rakam dizisi → TC/Öğrenci No olabilir
- "Kartım", "Numaram", "Hesabım" kelimeleriyle gelen rakamlar → Numara VAR

**D) KURUM/KİŞİ ADI ÇIKARIMI:**
- Büyük harfle başlayan kelimeler (Garanti, Vodafone, Mehmet Yılmaz) → İsim VAR
- "Banka", "Şirket", "Okul" kelimeleriyle birlikte geçen isimler → Kurum VAR

**E) KONU/OLAY ÇIKARIMI:**
- "Sınav notu", "Fatura itirazı", "Kaza" gibi özet ifadeler → Olay özeti VAR

---

### **ADIM 3: DİNAMİK EKSİKLİK TESPİTİ**
Şimdi {required_fields} listesindeki her alanı tek tek kontrol et:

**FOR EACH alan IN {required_fields}:**
1. **Hafıza kontrolü yap:** {context_data}'da geçiyor mu?
2. **Dolaylı çıkarım yap:** Yukarıdaki (ADIM 2) kurallarla bulunabilir mi?
3. **Eğer YOK ise:**
   - Bu alanı iste
   - **AMA sadece 1 ALAN sor** (Kullanıcıyı bunaltma)
4. **Eğer VAR ise:**
   - Listeye işaretle: ✅

---

### **ADIM 4: ESNEK SONLANDIRMA KURALLARI**

**BİTİRME ŞARTLARI (Herhangi biri geçerliyse):**
1. **Zorunlu alanların %80'i toplanmışsa** → BİTİR
2. **Aynı alan 3 kez sorulmuşsa ve cevap net değilse** → VAZGEÇ, o alanı es geç
3. **Toplam 5 soru sorulmuşsa** → ZORLA BİTİR (Loop koruması)
4. **Kullanıcı "Bilmiyorum / Geçelim / İstiyorum" gibi genel kelimeler kullandıysa** → O alanı atla

**✅ YENİ KURAL (VELİK/NAFAKA GİBİ KOMPOZİT ALANLAR İÇİN):**
- Eğer kullanıcı "Velayet istiyorum" veya "Nafaka istiyorum" diye COMBİNE TALEPİN ANA KELİMESİNİ söylediyse:
  - → **DETAY SORMA!** "istiyorum" kelimesi yeterli. Bilgi ALINMIŞ kabul et.
  - Örnek: "nafaka/tazminat anlaşması" alanı için kullanıcı "nafaka istiyorum" dediyse → ✅ TAMAM.


**ÖZEL DURUMLAR:**
- **OKUL kategorisi + Öğrenci numarası yoksa:**
  - → "Öğrenci numaranızı bilmiyorsanız, 'Yeni kayıt' veya 'Sonra eklerim' yazabilirsiniz."
- **BANKA kategorisi + Kart numarası eksikse:**
  - → "Kartın son 4 hanesini hatırlamıyorsanız, 'IBAN ile devam' yazabilirsiniz."
- **ADRES eksikse (Kaza/Belediye vb.):**
  - → "Tam adres bilmiyorsanız, en yakın belirgin yeri (okul/hastane/dükkan) belirtin."

---

### **ADIM 5: AKILLI SORU OLUŞTURMA**

Eksik bir alan bulduysan, **bağlama uygun** soru sor:

**Kategori Duyarlı Soru Şablonları:**
- **MAHKEME kategorisi:**
  - "Davalının tam adı nedir?"
  - "Tarafınıza tebliğ edilmiş bir belge/tarih var mı?"
- **OKUL kategorisi:**
  - "Hangi dersin notunda sorun var?"
  - "Sınavın tarihi neydi (Vize/Final/Bütünleme)?"
- **BANKA kategorisi:**
  - "İtiraz ettiğiniz işlemin tarihi ve tutarı nedir?"
  - "Kartın son 4 hanesi?"
- **BELEDİYE kategorisi:**
  - "Şikayetiniz hangi konuda? (Yol/Su/Çöp/Gürültü)"
  - "Sorunun olduğu sokak/mahalle?"

**GENEL KURAL:** Kullanıcıya **1 SORU**, **KISA CÜMLE**, **NET İSTEK**.

---

## 📤 **ÇIKTI FORMATI (JSON):**

{{
    "status": "BİLGİLER_TAM" (Yeterli veri toplandıysa) veya "DEVAM" (Eksik varsa),
    "message": "..." (Sadece eksik olan VE daha önce sorulmamış 1 veriyi iste),
    "collected_fields": ["alan1", "alan2", ...] (İsteğe bağlı - hangi alanlar toplandı)
}}

---

## 🚨 **KRİTİK HATIRLATMALAR:**
1. **ASLA aynı soruyu 2 kez sorma.** {context_data}'yı DİKKATLE oku.
2. **Kullanıcı "Bilmiyorum" derse o alanı atla.**
3. **5 sorudan sonra ZORLA "BİLGİLER_TAM" döndür.**
4. **{required_fields} listesindeki tüm alanlar eksik olsa bile, kullanıcının verdiği olay özeti yeterliyse BİTİR.**

---

**SON KONTROL (Kendine Sor):**
- ✅ Daha önce bu veriyi sordum mu?
- ✅ Kullanıcı dolaylı olarak bu veriyi verdi mi?
- ✅ 5 soruya ulaştım mı?
- ✅ Kullanıcı "Bilmiyorum" dedi mi?

Eğer yukarıdakilerden biri EVET ise → **SORMA!**
"""

WRITER_PROMPT = """
Sen **Türkiye'nin En İyi Resmi Yazışma ve Dilekçe Uzmanısın.**
Görevin: Vatandaşın verdiği dağınık bilgileri alıp; Mahkemelerin, Üniversitelerin, Bankaların ve Kamu Kurumlarının "Kabul Edeceği" standartlarda, hatasız ve ciddiyet dolu belgelere dönüştürmektir.

BAĞLAM VE VERİLER:
{context_data}

✍️ **YAZIM KURALLARI VE FORMAT DEVRİMİ (BUNLARA KESİN UY):**
1.  **DİKTATÖR KURAL (FORMAT YASAĞI):** Metin gövdesine (draft_content) **ASLA** HTML etiketleri (<br>, <p>, <b>) VEYA Markdown işaretleri (**, #, -, *) KOYMA.** Sadece düz metin üret. Yeni paragraf için sadece tek bir satır boşluk bırak.

1.  **DİNAMİK BAŞLIK MİMARİSİ (En Kritik Kural):**
    * **ASLA "İLGİLİ MAKAMA" YAZMA.** Bu amatörlüktür.
    * **Eğer Konu OKUL/EĞİTİM ise:**
        * Başlık: "T.C. [ÜNİVERSİTE/OKUL ADI] DEKANLIĞINA" veya "MÜDÜRLÜĞÜNE" (Okul adı yoksa [...] bırak).
        * Kimlik Bloğu: "DAVACI" YAZMA. Yerine: **"ÖĞRENCİ:"**, **"NUMARA:"**, **"BÖLÜM:"** başlıklarını kullan.
    * **Eğer Konu BANKA/KURUMSAL ise:**
        * Başlık: "[BANKA/KURUM ADI] GENEL MÜDÜRLÜĞÜNE"
        * Kimlik Bloğu: "DAVACI" YAZMA. Yerine: **"MÜŞTERİ:"**, **"TCKN:"**, **"KART/ABONE NO:"** başlıklarını kullan.
    * **Eğer Konu MAHKEME/YARGI ise:**
        * Standart Hukuk Formatı: **"DAVACI:"**, **"DAVALI:"**, **"KONU:"** yapısını koru.
    * **Eğer Konu BELEDİYE ise:**
        * Başlık: "T.C. [İLÇE] BELEDİYE BAŞKANLIĞINA"

2.  **DİL VE ÜSLUP (VATANDAŞ AĞZI):**
    * Kesinlikle **1. Tekil Şahıs (Ben / Tarafım)** kullan.
    * YASAKLI KELİMELER: "Müvekkil", "Müvekkilim", "Danışan". (Sen avukat değil, vatandaşın bizzat kendisiymiş gibi yazıyorsun).
    * Ciddiyet: Duygu sömürüsü yapma. "Çok üzüldüm" deme, "Manevi ızdırap duymaktayım" veya "Mağduriyetimin giderilmesi" de.

3.  **İÇERİK ZEKASI:**
    * **Tarih (KRİTİK):** Kullanıcının verdiği "Dün", "Geçen Hafta" gibi göreceli zaman ifadelerini, Bağlam'da bulunan **BUGÜNÜN TARİHİNE** göre hesaplayıp metne **net bir tarih** (Örn: 11.12.2025) olarak yaz.
    * **TARİH KURALI:** Asla ALAKASIZ BİR TARİH (Örn: 2023/2024) UYDURMA.
    * **Okul için:** "Sehven girilen notun düzeltilmesi", "Maddi hata incelemesi" gibi akademik terimler kullan.
    * **Banka için:** "Harcama itirazı (Chargeback)", "Provizyon iptali", "Haksız kesinti" gibi bankacılık terimleri kullan.

ÇIKTI FORMATI (JSON):
{{
    "status": "TASLAK_HAZIR",
    "draft_content": "..." (Buraya sadece saf dilekçe metnini yaz. HTML etiketi veya Markdown kullanma.)
}}
"""


CRITIC_PROMPT = """
Sen, hukuk bürosunun en kıdemli ve **HATA KABUL ETMEYEN BAŞDENETÇİSİSİN (Chief Auditor).**
Görevin: Önüne gelen taslağı, hitap ettiği kurumun (Mahkeme, Okul, Banka, Belediye) kurallarına göre denetlemektir.

İNCELENECEK TASLAK:
{draft_content}

MEVZUAT HAVUZU (RAG):
{rag_context}

🔍 **4 BOYUTLU DENETİM PROTOKOLÜ (Bunları Tek Tek Kontrol Et):**

1.  **KURUMSAL VE USUL UYUMU (PROTOCOL CHECK):**
    * **Eğer Konu OKUL ise:** Hitap "Dekanlık/Müdürlük" mü? "Davacı" kelimesi kullanılmış mı? (Kullanıldıysa: KIRMIZI KART). Öğrenci No var mı?
    * **Eğer Konu MAHKEME ise:** HMK usulüne uygun mu? "Davacı/Davalı" net mi? Talep sonucu var mı?
    * **Eğer Konu BANKA/BELEDİYE ise:** İlgili hesap/abone numarası metinde geçiyor mu?

2.  **MANTIK VE TUTARLILIK (LOGIC CHECK):**
    * Tarihler birbirini tutuyor mu? (Örn: Olay yarın olmuş gibi yazılmış mı?)
    * Talep kısmı, olay örgüsüyle örtüşüyor mu? (Adam iade istiyor, dilekçe tamir mi istiyor?)

3.  **DİL VE ÜSLUP (TONE CHECK):**
    * Vatandaş ağzı (1. Tekil Şahıs - "Ben") korunmuş mu?
    * "Müvekkil" kelimesi kaçmış mı? (Varsa reddet).
    * Ciddiyet korunmuş mu? (Duygu sömürüsü veya argo var mı?)

4.  **HUKUKİ DAYANAK (LEGAL CHECK):**
    * İddia edilen olay, genel hukuktaki veya yönetmelikteki bir maddeye (Örn: Ayıplı Mal, Maddi Hata) atıfta bulunuyor mu?

ÇIKTI FORMATI (JSON):
{{
    "critique": "...", (Saptanan hataları veya 'YAYINA UYGUNDUR' onayını içeren profesyonel rapor)
    "missing_laws": ["..."],
    "improvement_suggestions": ["..."] (Varsa düzeltme önerileri)
}}
"""


FINALIZER_PROMPT = """
Sen hukuk bürosunun **YÖNETİCİ ORTAĞI (MANAGING PARTNER)** ve **KURUMSAL FORMAT MİMARISIN.**
Görevin: Avukatın (Writer) yazdığı taslağı alıp, KURUMA UYGUN PROFESYONEL FORMATA dönüştürmektir.

TASLAK:
{draft_content}

DENETÇİ RAPORU:
{critique}

KATEGORİ KODU:
{category_key}

---

## 📋 FORMAT SEÇİM MANTIĞI (EN ÖNEMLİ KURAL)

**ADIM 1: KURUM TESPİTİ**
- Kategori kodu içinde **"egitim"** veya **"kyk"** geçiyorsa → OKUL FORMATI
- Kategori kodu içinde **"banka"** veya **"kredi"** geçiyorsa → BANKA FORMATI
- Kategori kodu içinde **"belediye"** geçiyorsa → BELEDİYE FORMATI
- Kategori kodu içinde **"tuketici"** geçiyorsa → TÜKETİCİ HAKEM HEYETİ FORMATI
- Kategori kodu içinde **"aile"**, **"is_"**, **"kira"**, **"icra"**, **"ceza"** geçiyorsa → MAHKEME FORMATI
- Eğer hiçbiri değilse → MAHKEME FORMATI (varsayılan)

---

## 🔧 FORMAT UYGULAMA KURALLARI

### **1. BAŞLIK (hitap_makam) KURALLARI:**

**OKUL İÇİN:**
- Kurum belli ise: "T.C. [ÜNİVERSİTE ADI] [FAKÜLTE/BÖLÜM] DEKANLIĞINA"
- Belli değilse: "T.C. [...] ÜNİVERSİTESİ [...] FAKÜLTESİ DEKANLIĞINA"

**MAHKEME İÇİN:**
- Boşanma ise: "T.C. NÖBETÇİ AİLE MAHKEMESİ SAYIN HAKİMLİĞİNE"
- Borç/İş ise: "T.C. NÖBETÇİ ASLİYE HUKUK MAHKEMESİ SAYIN HAKİMLİĞİNE"
- Ceza ise: "T.C. [...] CUMHURIYET BAŞSAVCIĞINA"

**BANKA İÇİN:**
- "[BANKA ADI] GENEL MÜDÜRLÜĞÜNE"
- Şube belli ise: "[BANKA ADI] [...] ŞUBESİ MÜDÜRLÜĞÜNE"

**BELEDİYE İÇİN:**
- "T.C. [İLÇE ADI] BELEDİYE BAŞKANLIĞINA"
- Özel birime gidiyorsa: "T.C. [İLÇE] BELEDİYESİ FEN İŞLERİ DAİRE BAŞKANLIĞINA"

**TÜKETİCİ İÇİN:**
- "T.C. TÜKETİCİ HAKEM HEYETİ BAŞKANLIĞI'NA ([İL ADI])"

**⚠️ KRİTİK KURAL:** Başlık **ASLA** `dilekce_metni` içine gömülmemeli! Sadece `hitap_makam` alanına yazılmalı!

**OKUL İÇİN (egitim kategorisi):**
- Eğer fakülte/bölüm belirtilmişse:
  * "T.C. [...] ÜNİVERSİTESİ MÜHENDİSLİK FAKÜLTESİ DEKANLIĞINA"
  * (Üniversite adı bilinmiyorsa [...] ile placeholder bırak)
  
- Eğer sadece "Mühendislik Fakültesi" denilmişse:
  * "T.C. [...] ÜNİVERSİTESİ MÜHENDİSLİK FAKÜLTESİ DEKANLIĞINA"

**ÖNEMLI:** 
1. Başlık `hitap_makam` değişkenine YAZ
2. `dilekce_metni` içinde **ASLA** başlık tekrar etme
3. `dilekce_metni` direkt **ÖĞRENCİ BİLGİLERİ** ile başlamalı

---

### **2. KİMLİK BLOĞU (KURUMA GÖRE)**

**OKUL:** "ÖĞRENCİ BİLGİLERİ" başlığı altında → Öğrenci No, Bölüm/Sınıf
**MAHKEME:** "DAVACI BİLGİLERİ" ve "DAVALI BİLGİLERİ" ayrı ayrı
**BANKA:** "MÜŞTERİ BİLGİLERİ" başlığı altında → Müşteri/Hesap No
**BELEDİYE:** "BAŞVURAN BİLGİLERİ" başlığı
**TÜKETİCİ:** "BAŞVURU SAHİBİ (TÜKETİCİ)" ve "KARŞI TARAF" ayrı bölümler

---

### **3. İÇERİK YAPILANDIRMA**

Writer'dan gelen metni analiz et ve şu bölümlere ayır:

**A) AÇIKLAMALAR:** Olayın kronolojik anlatımı
**B) HUKUKİ DAYANAK:** İlgili kanun/yönetmelik maddeleri
**C) TALEPLER:** Net istek listesi (madde madde)
**D) EKLER:** Belgeler listesi

**KURAL:** Metin içindeki gereksiz HTML/Markdown etiketlerini TEMİZLE.

Writer'dan gelen metni analiz et ve şu bölümlere ayır:

**⚠️ ÖNCELİKLE HTML/MARKDOWN TEMİZLE:**
- Writer'ın `draft_content` içinde `<br>`, `<b>`, `**`, `##` gibi etiketler varsa → TAMAMI SİL!
- Sadece DÜZ METİN olmalı
- Paragraf arası boşluk için sadece `\n\n` kullan

**Sonra Yapılandır:**
**A) ÖĞRENCİ BİLGİLERİ:** (OKUL formatı için)
   - Öğrenci No: ...
   - Bölüm/Sınıf: ...
   - T.C. Kimlik No: ...
   
**B) AÇIKLAMALAR:** Olayın kronolojik anlatımı

**C) HUKUKİ DAYANAK:** İlgili kanun/yönetmelik maddeleri

**D) TALEPLER:** Net istek listesi

**E) EKLER:** Belgeler listesi

---

### **4. SONUÇ BÖLÜMÜ (KURUMA GÖRE)**

**OKUL:** "Bilgilerinize arz ederim."
**MAHKEME:** "Gereğini saygılarımla arz ederim." (Resmi ton)
**BANKA:** "Gereğini arz ederim." (Kurumsal ton)
**BELEDİYE:** "Gereğini saygılarımla arz ederim."
**TÜKETİCİ:** "Yasal haklarım saklı kalmak kaydıyla, hak ve hukuk kaybımın önlenmesini talep ederim."

---

## 📤 ÇIKTI FORMATI (JSON):

{{
    "status": "DILEKCE_HAZIR",
    "hitap_makam": "...", (Sadece başlık, örn: T.C. NÖBETÇİ AİLE MAHKEMESİNE)
    "dilekce_metni": "...", (KİMLİK BLOĞU + GÖVDE - temiz metin, HTML yok)
    "hukuki_oneriler": "...", (Adım adım eylem planı)
    "improvement_note": "...", (Yapılan iyileştirme özeti)
    "template_used": "...", (Hangi şablon kullanıldı: mahkeme/okul/banka/belediye/tuketici)
    "graph_data": {{
        "nodes": [
            {{"id": 1, "label": "...", "group": "person"}},
            {{"id": 2, "label": "...", "group": "person"}},
            {{"id": 3, "label": "...", "group": "event"}},
            {{"id": 4, "label": "...", "group": "law"}}
        ],
        "edges": [
            {{"from": 1, "to": 2, "label": "Başvuruyor"}},
            {{"from": 2, "to": 3, "label": "İşlem Yaptı"}},
            {{"from": 3, "to": 4, "label": "Gereğince"}}
        ]
    }}
}}

---

## ⚠️ KRİTİK HATIRLATMALAR:

1. **ASLA HTML/MARKDOWN KOYMA:** `dilekce_metni` içinde sadece düz metin olsun. `<br>`, `**`, `#` yasak.
2. **KURUMA UYGUN DİL:** Okula "Sayın Hocam", Mahkemeye "Sayın Hakimlik", Bankaya "Sayın Yetkililer"
3. **TARİH KONTROLÜ:** "Dün", "Geçen hafta" gibi ifadeleri somut tarihe çevir.
4. **EKLER BÖLÜMÜ:** Mutlaka ekle (Fatura, Kimlik Fotokopisi, Dekont vb.)
5. **graph_data asla boş olamaz** - en az 2 node olmalı.

**SON KONTROL:**
- ✅ Doğru şablon seçildi mi? ({category_key} koduna göre)
- ✅ Başlık kuruma uygun mu?
- ✅ Kimlik bloğu standartlara uygun mu?
- ✅ Metin HTML'den temiz mi?
"""



CATEGORIES = {

"tuketici_ayipli_mal": {
"title": "Ayıplı Mal (Ürün İadesi/Değişimi)",
"law": "6502 Sayılı Kanun Md. 11",
"required_fields": ["ürün", "satıcı", "fatura tarihi", "ayıp konusu"]
},
"tuketici_hizmet_kusuru": {
"title": "Ayıplı Hizmet (İnternet/Tamirat/Tatil)",
"law": "6502 Sayılı Kanun Md. 13-16",
"required_fields": ["hizmet sağlayıcı", "sözleşme tarihi", "sorun"]
},
"tuketici_hakem_heyeti": {
"title": "Hakem Heyeti Başvuru Dilekçesi",
"law": "Tüketici Hakem Heyetleri Yönetmeliği",
"required_fields": ["uyuşmazlık bedeli", "talep"]
},

"kira_tahliye_temerrut": {
"title": "Kira Ödenmemesi Nedeniyle Tahliye (Temerrüt)",
"law": "TBK Md. 315",
"required_fields": ["kira miktarı", "ödenmeyen aylar", "ihtarname tarihi"]
},
"kira_tahliye_ihtiyac": {
"title": "Gereksinim (İhtiyaç) Nedeniyle Tahliye",
"law": "TBK Md. 350",
"required_fields": ["taşınmaz adresi", "ihtiyaç sahibi (kendisi/oğlu vs)"]
},
"kira_bedel_tespit": {
"title": "Kira Tespit Davası (5 Yıl Üzeri)",
"law": "TBK Md. 344",
"required_fields": ["kira başlangıç tarihi", "mevcut kira", "talep edilen kira"]
},
"kira_uyarlama": {
"title": "Kira Uyarlama Davası (Aşırı İfa Güçlüğü)",
"law": "TBK Md. 138",
"required_fields": ["olağanüstü durum", "ekonomik gerekçe"]
},

"is_ise_iade": {
"title": "İşe İade Davası (Geçersiz Fesih)",
"law": "İş Kanunu Md. 18-21",
"required_fields": ["işyeri çalışan sayısı", "kıdem süresi", "fesih tarihi"]
},
"is_alacak": {
"title": "Kıdem, İhbar ve Fazla Mesai Alacağı",
"law": "İş Kanunu & TBK",
"required_fields": ["işe giriş-çıkış tarihi", "son brüt ücret"]
},
"is_mobbing": {
"title": "Mobbing (Psikolojik Taciz) Nedeniyle Fesih",
"law": "TBK Md. 417 & İş Kanunu Md. 24",
"required_fields": ["mobbing detayları", "tanık var mı"]
},

"aile_anlasmali_bosanma": {
"title": "Anlaşmalı Boşanma Protokolü/Dilekçesi",
"law": "TMK Md. 166/3",
"required_fields": ["evlilik süresi (1 yıl şartı)", "nafaka/tazminat anlaşması"]
},
"aile_cekismeli_bosanma": {
"title": "Çekişmeli Boşanma (Şiddet/Zina/Geçimsizlik)",
"law": "TMK Md. 161-166",
"required_fields": ["boşanma sebebi", "kusur durumu", "talepler"]
},
"aile_nafaka_artirim": {
"title": "Nafaka Artırım Davası",
"law": "TMK Md. 176",
"required_fields": ["mevcut nafaka", "ekonomik değişiklikler"]
},

"ceza_sikayet": {
"title": "Savcılık Suç Duyurusu (Genel)",
"law": "CMK Md. 158",
"required_fields": ["olay yeri", "olay tarihi", "şüpheli bilgisi"]
},
"bilisim_erisimi_engelleme": {
"title": "İnternet İçerik Kaldırma / Erişim Engeli",
"law": "5651 Sayılı Kanun Md. 9",
"required_fields": ["URL adresi", "ihlal edilen hak (özel hayat/kişilik)"]
},
"bilisim_dolandiricilik": {
"title": "Bilişim Yoluyla Dolandırıcılık",
"law": "TCK Md. 158/1-f",
"required_fields": ["banka/kredi kartı", "site adı", "tutar"]
},

"icra_itiraz": {
"title": "İcra Takibine İtiraz (Borca/İmzaya)",
"law": "İİK Md. 62",
"required_fields": ["dosya no", "icra dairesi", "itiraz nedeni"]
},
"icra_menfi_tespit": {
"title": "Menfi Tespit (Borçlu Olmadığının Tespiti)",
"law": "İİK Md. 72",
"required_fields": ["icra dosya no", "dayanak belge"]
},

"trafik_ceza_iptal": {
"title": "Trafik Cezası İptali",
"law": "Kabahatler Kanunu & KTK",
"required_fields": ["ceza tutanak seri no", "tebliğ tarihi"]
},
"trafik_deger_kaybi": {
"title": "Araç Değer Kaybı Başvurusu",
"law": "KTK & Sigorta Genel Şartları",
"required_fields": ["kaza tarihi", "ekspertiz raporu"]
},

"egitim_universite_sinav_itiraz": {
"title": "Üniversite Sınav Notuna İtiraz (Maddi Hata)",
"law": "Yükseköğretim Kurumları Sınav ve Değerlendirme Yönetmeliği",
"required_fields": ["fakülte/bölüm", "dersin adı", "sınav türü (vize/final)", "öğrenci numarası"]
},
"egitim_universite_kayit_dondurma": {
"title": "Üniversite Kayıt Dondurma Talebi",
"law": "Yükseköğretim Kurumları Lisans Eğitim-Öğretim Yönetmeliği",
"required_fields": ["fakülte/bölüm", "öğrenci numarası", "dondurma gerekçesi (sağlık/maddi)", "dondurulacak yarıyıl"]
},
"egitim_universite_yaz_okulu": {
"title": "Yaz Okulu / Üstten Ders Alma Talebi",
"law": "Üniversite Senatosu Yaz Okulu Yönetmeliği",
"required_fields": ["alınmak istenen dersler", "öğrenci numarası", "gerekçe (mezuniyet vb.)"]
},


"egitim_meb_sinav_itiraz": {
"title": "Okul (MEB) Sınav/Karne Notuna İtiraz",
"law": "MEB Okul Öncesi ve İlköğretim Kurumları Yönetmeliği",
"required_fields": ["okul adı", "sınıf/şube", "öğrenci adı soyadı", "velisi olduğum öğrenci", "ders adı"]
},
"egitim_meb_nakil": {
"title": "Okul Nakil / Geçiş Talebi",
"law": "MEB Ortaöğretim Kurumları Yönetmeliği (Nakil Esasları)",
"required_fields": ["mevcut okul", "gitmek istenen okul", "nakil gerekçesi (adres değişikliği vb.)", "öğrenci T.C."]
},


"egitim_kyk_yurt_itiraz": {
"title": "KYK Yurt Başvuru/Disiplin İtirazı",
"law": "Yükseköğrenim Kredi ve Yurtlar Kurumu Yurt İdare Yönetmeliği",
"required_fields": ["yurt adı", "blok/oda no", "öğrenci t.c.", "talep konusu (izin/giriş saati/ceza)"]
},
"egitim_kyk_kayit_silme": {
"title": "KYK Yurt Kayıt Sildirme / Depozito İadesi",
"law": "GSB Yurt Hizmetleri Yönetmeliği",
"required_fields": ["yurt adı", "ayrılış tarihi", "IBAN (depozito iadesi için)", "öğrenci t.c."]
},
"egitim_diploma_talep": {
"title": "Diploma / Geçici Mezuniyet Belgesi Talebi (Kayıp)",
"law": "Resmî Belgede Sahtecilik ve Belge Düzenleme Esasları",
"required_fields": ["mezun olunan okul/bölüm", "mezuniyet yılı", "talep nedeni (kayıp/yıpranma)", "gazete ilanı (varsa)"]
},



"belediye_altyapi_sikayet": {
"title": "Belediye Altyapı/Hizmet Şikayeti (Bozuk Yol/Su/Çöp)",
"law": "5393 Sayılı Belediye Kanunu (Hemşeri Hukuku)",
"required_fields": ["şikayet konusu (yol/su/aydınlatma)", "açık adres (sokak/mahalle)", "tehlike durumu"]
},
"belediye_imar_durumu": {
 "title": "İmar Durumu Belgesi Talebi",
"law": "3194 Sayılı İmar Kanunu",
"required_fields": ["taşınmaz adresi", "ada/parsel numarası", "tapu sahibi"]
},
"belediye_zabita_sikayet": {
"title": "Zabıta Şikayeti (Gürültü/Fahiş Fiyat/Kaldırım İşgali)",
"law": "Kabahatler Kanunu & Belediye Zabıta Yönetmeliği",
"required_fields": ["şikayet edilen yer/kişi", "olay saati", "konu (gürültü/işgal)", "adres"]
},
"belediye_sosyal_yardim": {
"title": "Sosyal Yardım Başvurusu (Erzak/Kömür/Nakit)",
"law": "Sosyal Hizmetler Kanunu",
"required_fields": ["hane halkı sayısı", "aylık gelir durumu", "talep edilen yardım türü"]
},


"banka_harcama_itiraz": {
"title": "Kredi Kartı Harcama İtirazı (Ters İbraz)",
"law": "5464 Sayılı Banka Kartları Kanunu",
"required_fields": ["banka adı", "işlem tarihi", "işlem tutarı", "işyeri adı", "kart son 4 hane"]
},
"banka_kredi_yapilandirma": {
"title": "Kredi Borcu Yapılandırma / Ödeme Güçlüğü",
"law": "BDDK Yönetmelikleri & TBK",
"required_fields": ["kredi türü (konut/ihtiyaç)", "kalan borç tutarı", "ödeme güçlüğü nedeni (işsizlik vb.)", "müşteri no"]
},
"banka_blok_kaldirma": {
"title": "Hesap/Kart Blokesi Kaldırma Talebi",
"law": "Bankacılık Kanunu & MASAK Mevzuatı",
"required_fields": ["hesap/kart no", "bloke nedeni (biliniyorsa)", "mağduriyet durumu"]
},


"kurum_abonelik_iptal": {
"title": "Abonelik İptali (İnternet/TV/Doğalgaz)",
"law": "Abonelik Sözleşmeleri Yönetmeliği (Md. 23)",
"required_fields": ["kurum adı", "abone/hizmet numarası", "iptal gerekçesi (taşınma/pahalı)"]
},
"kurum_fatura_itiraz": {
"title": "Fatura İtirazı (Yüksek/Hatalı Fatura)",
"law": "Tüketicinin Korunması Hakkında Kanun",
"required_fields": ["kurum adı", "fatura dönemi", "fatura tutarı", "normalde gelen ortalama tutar", "abone no"]
},
}



INSTITUTION_TEMPLATES = {
    
    "mahkeme": """T.C. {hitap_makam}

**DAVACI BİLGİLERİ**
Adı Soyadı: {ad_soyad}
T.C. Kimlik No: {tckn}
Adres: {adres}
Telefon: {telefon}
E-posta: {email}

**DAVALI BİLGİLERİ**
{davali_bilgileri}

---

**KONU:** {konu_baslik}

**AÇIKLAMALAR:**
{aciklamalar}

**HUKUKİ DAYANAK:**
{hukuki_dayanak}

**TALEP:**
{talepler}

**EKLER:**
{ekler}

---

**Tarih:** {tarih}
**Davacı Adı Soyadı:** {ad_soyad}
**İmza:**
{imza_resmi}""",

    
    "okul": """T.C. {hitap_makam}

**ÖĞRENCİ BİLGİLERİ**
Adı Soyadı: {ad_soyad}
Öğrenci No: {ogrenci_no}
Bölüm/Sınıf: {bolum}
T.C. Kimlik No: {tckn}
Telefon: {telefon}
E-posta: {email}

---

**KONU:** {konu_baslik}

**AÇIKLAMALAR:**
{aciklamalar}

**İLGİLİ YÖNETMELİK/MEVZUAT:**
{hukuki_dayanak}

**TALEBİM:**
{talepler}

**EKLER:**
{ekler}

---

Bilgilerinize arz ederim.

**Tarih:** {tarih}
**Öğrenci Adı Soyadı:** {ad_soyad}
**İmza:**
{imza_resmi}""",

    
    "banka": """{hitap_makam}

**MÜŞTERİ BİLGİLERİ**
Adı Soyadı: {ad_soyad}
T.C. Kimlik No: {tckn}
Müşteri/Hesap No: {musteri_no}
Telefon: {telefon}
E-posta: {email}
Adres: {adres}

---

**KONU:** {konu_baslik}

**AÇIKLAMALAR:**
{aciklamalar}

**YASAL DAYANAK:**
{hukuki_dayanak}

**TALEBİM:**
{talepler}

**EKLER:**
{ekler}

---

Gereğini arz ederim.

**Tarih:** {tarih}
**Müşteri Adı Soyadı:** {ad_soyad}
**İmza:**
{imza_resmi}""",

    
    "belediye": """T.C. {hitap_makam}

**BAŞVURAN BİLGİLERİ**
Adı Soyadı: {ad_soyad}
T.C. Kimlik No: {tckn}
Adres: {adres}
Telefon: {telefon}
E-posta: {email}

---

**KONU:** {konu_baslik}

**AÇIKLAMALAR:**
{aciklamalar}

**İLGİLİ MEVZUAT:**
{hukuki_dayanak}

**TALEBİM:**
{talepler}

**EKLER:**
{ekler}

---

Gereğini saygılarımla arz ederim.

**Tarih:** {tarih}
**Başvuran Adı Soyadı:** {ad_soyad}
**İmza:**
{imza_resmi}""",

    # 5. TÜKETİCİ HAKEM HEYETİ (Özel Format)
    "tuketici": """T.C.
TÜKETİCİ HAKEM HEYETİ BAŞKANLIĞI'NA
({il_adi})

**BAŞVURU SAHİBİ (TÜKETİCİ)**
Adı Soyadı: {ad_soyad}
T.C. Kimlik No: {tckn}
Adres: {adres}
Telefon: {telefon}
E-posta: {email}

**KARŞI TARAF (SATICI/SAĞLAYICI)**
Unvanı: {satici_unvan}
Adres: {satici_adres}
MERSİS No: {mersis_no}

---

**KONU:** {konu_baslik}

**AÇIKLAMALAR**
{aciklamalar}

**HUKUKİ DAYANAK**
{hukuki_dayanak}

**TALEPLERİM**
{talepler}

**EKLER:**
{ekler}

---

**Tarih:** {tarih}
**Ad Soyad:** {ad_soyad}
**İmza:**
{imza_resmi}"""
}




def get_template_for_category(category_key):
    """Kategori koduna göre doğru şablon anahtarını döner."""
    if any(x in category_key for x in ["aile", "is_", "kira", "icra", "ceza"]):
        return "mahkeme"
    elif "egitim" in category_key or "kyk" in category_key:
        return "okul"
    elif "banka" in category_key or "kredi" in category_key:
        return "banka"
    elif "belediye" in category_key:
        return "belediye"
    elif "tuketici" in category_key:
        return "tuketici"
    else:
        return "mahkeme"

PETITION_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{
    font-family: 'Times New Roman', serif;
    font-size: 12pt;
    line-height: 1.6;
    margin: 3cm 2.5cm 2.5cm 2.5cm;
    color: #000;
}}

/* BAŞLIK */
.header {{
    text-align: center;
    font-weight: bold;
    font-size: 13pt;
    margin-bottom: 30px;
}}

/* KİMLİK BLOĞU (Sol Üst) */
.identity-block {{
    margin-bottom: 25px;
    line-height: 1.4;
}}

.identity-block strong {{
    display: inline-block;
    min-width: 140px;
    font-weight: bold;
}}

/* BÖLÜM BAŞLIKLARI */
.section-title {{
    font-weight: bold;
    text-decoration: underline;
    margin-top: 20px;
    margin-bottom: 10px;
    font-size: 12pt;
}}

/* PARAGRAFLAR */
.section-content {{
    text-align: justify;
    text-indent: 30px;
    margin-bottom: 15px;
}}

/* ALT BİLGİ (Tarih ve İmza) */
.footer {{
    margin-top: 50px;
    text-align: right;
}}

.signature-box {{
    display: inline-block;
    text-align: center;
    margin-top: 20px;
    min-width: 200px;
}}

.signature-img {{
    max-height: 80px;
    max-width: 150px;
    display: block;
    margin: 5px auto;
}}

/* QR KOD (Sağ Üst) */
.qr-code {{
    position: absolute;
    top: 20px;
    right: 20px;
    text-align: center;
}}

.qr-code img {{
    width: 80px;
    display: block;
}}

.qr-code span {{
    font-size: 8px;
    color: #666;
}}

/* HUKUKİ EK SAYFA */
.legal-appendix {{
    page-break-before: always;
    border: 1px solid #333;
    padding: 20px;
    background-color: #f9f9f9;
    font-family: Arial, sans-serif;
    font-size: 10pt;
}}

.legal-appendix h3 {{
    border-bottom: 2px solid #d97706;
    padding-bottom: 10px;
    color: #0f172a;
}}

.ai-meta {{
    font-size: 8pt;
    color: #666;
    margin-top: 20px;
    text-align: center;
    border-top: 1px dashed #ccc;
    padding-top: 10px;
}}
</style>
</head>
<body>

<!-- QR KOD -->
<div class="qr-code">
    {qr_kod_html}
</div>

<!-- BAŞLIK -->
<div class="header">
    {hitap_makam}
</div>

<!-- GÖVDE (KİMLİK BLOĞU + İÇERİK) -->
<div>
    {dilekce_metni}
</div>

<!-- ALT BİLGİ -->
<div class="footer">
    <p><strong>Tarih:</strong> {tarih}</p>
    <div class="signature-box">
        <p><strong>Ad Soyad:</strong><br>{ad_soyad}</p>
        {imza_resmi}
    </div>
</div>

<!-- EK SAYFA: HUKUKİ DAYANAK VE STRATEJİ -->
<div class="legal-appendix">
    <h3>📜 JusticAI Hukuki Dayanak ve Strateji Raporu</h3>
    
    <p><strong>⚖️ Hukuki Temel ve Mevzuat:</strong></p>
    <div style="margin-bottom: 20px;">
        {hukuki_oneriler}
    </div>
    
    <p><strong>🤖 Sistem İyileştirme Notu (AI Audit):</strong></p>
    <div style="background: #eef2ff; padding: 10px; border-left: 4px solid #4f46e5; margin-bottom: 10px;">
        {improvement_note}
    </div>
    
    <div class="ai-meta">
        Bu belge JusticAI Yapay Zeka Asistanı tarafından {tarih} tarihinde oluşturulmuştur.<br>
        KVKK kapsamında kişisel veriler maskelenerek işlenmiştir.<br>
        Referans ID: {tracking_number} | Dijital Mühür: {document_hash}
    </div>
</div>

</body>
</html>
"""
