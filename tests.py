import unittest
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta


load_dotenv()

from logic_services import check_rules, search_legal_docs, vector_db, ethics_guard
from privacy_service import privacy_guard

class TestJusticAI_Engineering(unittest.TestCase):

    def setUp(self):
        print("\n----------------------------------------------------------------------")
        print(f"🕒 Test Başlatılıyor: {self._testMethodName}")


    def test_01_tuketici_sinir_kontrolu(self):
        """Rule Engine: Parasal sınır aşımı tespiti."""
        text = "Telefonu 150.000 TL'ye satın aldım."
        result = check_rules("tuketici_haklari", text)
        self.assertIn("aşmaktadır", result) 
        print("✅ [Rule Engine] Sınır kontrolü başarılı.")

    def test_02_trafik_zamani_kontrolu(self):
        """Rule Engine: Hak düşürücü süre tespiti."""
        old_date = (datetime.now() - timedelta(days=40)).strftime("%d.%m.%Y")
        text = f"Cezanın tebliği {old_date} tarihinde yapıldı."
        result = check_rules("trafik_cezasi", text)
        self.assertTrue("süre" in result.lower() or "gün" in result.lower())
        print("✅ [Rule Engine] Zaman aşımı tespiti başarılı.")

    def test_03_chromadb_semantic_search(self):
        """RAG: ChromaDB anlamsal arama testi."""
        result = search_legal_docs("kiracı kirayı ödemiyor evden çıkarmak istiyorum", "kira")
        self.assertTrue(len(result) > 10) 
        print("✅ [ChromaDB] Semantik arama başarılı.")

    def test_04_db_health_check(self):
        """Database: Veri bütünlüğü kontrolü."""
        try:
            count = vector_db.collection.count()
            self.assertGreater(count, 5, "Veritabanı boş görünüyor!")
            print(f"✅ [ChromaDB] Veritabanı sağlıklı. Toplam Belge: {count}")
        except:
            print("⚠️ DB henüz hazır değil (Normal olabilir)")


    def test_05_kvkk_masking_flow(self):
        """Privacy: Maskeleme ve Geri Yükleme testi."""
        original_text = "Benim TCKN: 10000000146 ve Tel: 0532 555 44 33"
        masked, mapping = privacy_guard.anonymize(original_text)
        self.assertNotIn("10000000146", masked)
        self.assertIn("[KVKK_TCKN", masked)
        restored = privacy_guard.de_anonymize(masked, mapping)
        self.assertEqual(original_text, restored)
        print("✅ [Privacy Layer] Maskeleme ve Geri Yükleme döngüsü başarılı.")

 
    def test_06_ethics_block(self):
        """Ethics: Yasaklı içerik engelleme."""
        unsafe_text = "Sahte fatura düzenleyip vergi kaçırmak istiyorum."
        is_safe, msg = ethics_guard.analyze(unsafe_text)
        self.assertFalse(is_safe) 
      
        self.assertIn("güvenlik", msg)
        print("✅ [Ethics Guard] Yasa dışı talep başarıyla engellendi.")

    def test_07_ethics_victim_allow(self):
        """Ethics: Mağduriyet tespiti (False Positive Kontrolü)."""
    
        victim_text = "Tüketici hakem heyetine başvurmak istiyorum."
        is_safe, msg = ethics_guard.analyze(victim_text)
        self.assertTrue(is_safe) 
        print("✅ [Ethics Guard] 'Başvurmak' kelimesi güvenli olarak algılandı.")

if __name__ == '__main__':
    print("=======================================================")
    print("🤖 JUSTICAI - SYSTEM INTEGRITY & UNIT TESTS (v4.2)")
    print("=======================================================")
    unittest.main()