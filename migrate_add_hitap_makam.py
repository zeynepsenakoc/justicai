import sqlite3
import os

def migrate_database():
    """
    SQLite veritabanına 'hitap_makam' kolonu ekler.
    Eğer kolon zaten varsa hata vermez (safe).
    """
    
 
    db_path = "database.db"  
    
    if not os.path.exists(db_path):
        print(f"❌ HATA: Veritabanı dosyası bulunamadı: {db_path}")
        print("💡 İpucu: Bu scripti app.py'nin olduğu klasörde çalıştır.")
        return False
    
    try:
     
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        
        cursor.execute("PRAGMA table_info(petition)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "hitap_makam" in columns:
            print("ℹ️ 'hitap_makam' kolonu zaten mevcut. Migration gerekmiyor.")
            conn.close()
            return True
        
     
        print("🔧 Migration başlatılıyor...")
        cursor.execute("""
            ALTER TABLE petition 
            ADD COLUMN hitap_makam TEXT DEFAULT 'DİLEKÇE BAŞLIĞI YOK'
        """)
        
        conn.commit()
        print("✅ Migration başarılı! 'hitap_makam' kolonu eklendi.")
        
   
        cursor.execute("PRAGMA table_info(petition)")
        new_columns = [column[1] for column in cursor.fetchall()]
        
        if "hitap_makam" in new_columns:
            print("✅ Doğrulama başarılı: Kolon veritabanında görünüyor.")
        else:
            print("⚠️ UYARI: Kolon eklendi ama doğrulanamadı.")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ HATA: Migration başarısız: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("JusticAI - Database Migration Script")
    print("Petition tablosuna 'hitap_makam' kolonu ekleniyor...")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    print()
    if success:
        print("🎉 Migration tamamlandı!")
        print("📌 SONRAKİ ADIM: models.py dosyasını güncelle ve app.py'yi yeniden başlat.")
    else:
        print("❌ Migration başarısız oldu. Lütfen hataları kontrol et.")
    print("=" * 60)