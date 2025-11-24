import unittest
import time
from datetime import datetime, timedelta
from logic_services import check_rules, search_legal_docs, vector_db

class TestHukukAI(unittest.TestCase):

    def setUp(self):
        # Her testten önce veritabanını yeniden yükle (Garanti olsun)
        # Eğer mevzuat dosyası güncellendiyse belleğe alsın
        vector_db.docs = []
        vector_db.load_documents("legal_docs/mevzuat.txt")

    def test_01_tuketici_sinir_ustu(self):
        """SENARYO: 150.000 TL girildiğinde uyarı verilmeli."""
        print("\n[TEST 1] Tüketici Sınır Aşımı Kontrolü")
        text = "Telefonu 150.000 TL'ye satın aldım."
        result = check_rules("tuketici_haklari", text)
        self.assertIn("104.000 TL", result)
        self.assertIn("Mahkeme", result)
        print("✅ BAŞARILI")

    def test_02_tuketici_sinir_alti(self):
        """SENARYO: 50.000 TL girildiğinde uyarı VERİLMEMELİ."""
        print("\n[TEST 2] Geçerli Tutar Kontrolü")
        text = "Ürün bedeli 50.000 TL."
        result = check_rules("tuketici_haklari", text)
        self.assertEqual(result, "")
        print("✅ BAŞARILI")

    def test_03_trafik_suresi_gecmis_dinamik(self):
        """SENARYO: 40 gün önceki tarih girilirse 'Süre Aşımı' uyarısı verilmeli."""
        print("\n[TEST 3] Trafik Cezası Süre Aşımı (Dinamik Tarih)")
        # DİNAMİK TARİH: Bugünden 40 gün öncesini hesapla
        old_date = (datetime.now() - timedelta(days=40)).strftime("%d.%m.%Y")
        text = f"Cezanın tebliği {old_date} tarihinde yapıldı."
        
        result = check_rules("trafik_cezasi", text)
        self.assertTrue("süre" in result.lower() or "15 gün" in result.lower())
        print("✅ BAŞARILI")

    def test_04_ocr_veri_kaynagi_dinamik(self):
        """SENARYO: Kullanıcı yazmasa bile OCR verisindeki eski tarih yakalanmalı."""
        print("\n[TEST 4] OCR Kaynaklı Veri Kontrolü")
        user_input = "İtiraz ediyorum."
        # Dinamik tarih: 60 gün önce
        fail_date = (datetime.now() - timedelta(days=60)).strftime("%d.%m.%Y")
        ocr_input = f"Tebellüğ Tarihi: {fail_date}"
        
        result = check_rules("trafik_cezasi", user_input, ocr_input)
        self.assertIn(fail_date, result)
        print("✅ BAŞARILI")

    def test_05_rag_arama(self):
        """SENARYO: 'Tahliye' kelimesi aranınca Kira Kanunu bulunmalı."""
        print("\n[TEST 5] Vektör Arama (RAG) Kontrolü")
        # Eşik değerini düşürdüğümüz için artık bulması lazım
        result = search_legal_docs("kiracı evden çıkmıyor tahliye", "kira")
        self.assertIn("6098 SAYILI", result)
        print("✅ BAŞARILI")

    def test_06_veritabani_yuklendi_mi(self):
        """SENARYO: Mevzuat veritabanı dolu mu?"""
        print("\n[TEST 6] Bilgi Bankası Sağlık Kontrolü")
        doc_count = len(vector_db.docs)
        print(f"   -> Yüklü Belge Sayısı: {doc_count}")
        # Genişletilmiş veritabanında en az 10 madde olmalı
        self.assertGreaterEqual(doc_count, 10, f"Veritabanı eksik yüklendi! ({doc_count})")
        print("✅ BAŞARILI")

if __name__ == '__main__':
    print("=======================================================")
    print("🤖 HUKUK AI - SYSTEM INTEGRITY TESTS (v3.0)")
    print("=======================================================")
    unittest.main()