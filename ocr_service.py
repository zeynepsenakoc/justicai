import os
import uuid
import logging
import pytesseract
import filetype
from pdf2image import convert_from_path
from PIL import Image
from werkzeug.utils import secure_filename

# Loglama ayarı
logger = logging.getLogger(__name__)

# Ayarlar
UPLOAD_FOLDER = 'uploads'
ALLOWED_MIME_TYPES = [
    'image/jpeg', 
    'image/png', 
    'image/heic', 
    'application/pdf'
]
# 16 MB Limit
MAX_FILE_SIZE = 16 * 1024 * 1024  

# Yükleme klasörü yoksa oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_file_safe(file_path):
    """
    Dosyanın sadece uzantısına bakmaz, 'Magic Byte'larını okuyarak
    gerçekten resim veya PDF olup olmadığını kontrol eder.
    """
    kind = filetype.guess(file_path)
    if kind is None:
        return False
    if kind.mime not in ALLOWED_MIME_TYPES:
        logger.warning(f"Güvensiz dosya tipi tespit edildi: {kind.mime}")
        return False
    return True

def extract_text_from_file(file_storage):
    """
    Flask'tan gelen dosyayı güvenli şekilde kaydeder, okur, siler.
    """
    # 1. GÜVENLİ DOSYA ADI (UUID)
    ext = os.path.splitext(file_storage.filename)[1].lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        # Dosyayı geçici kaydet
        file_storage.save(file_path)

        # 2. BOYUT KONTROLÜ
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            os.remove(file_path)
            return {"error": "Dosya boyutu 16MB'dan büyük olamaz."}

        # 3. İÇERİK TÜRÜ KONTROLÜ (GÜVENLİK)
        if not is_file_safe(file_path):
            os.remove(file_path)
            return {"error": "Geçersiz veya güvensiz dosya formatı. Sadece Resim ve PDF."}

        text_result = ""

        # 4. OCR İŞLEMİ
        if file_path.endswith('.pdf'):
            # PDF ise sayfa sayfa oku
            try:
                pages = convert_from_path(file_path)
                for page in pages:
                    text = pytesseract.image_to_string(page, lang='tur')
                    text_result += text + "\n"
            except Exception as e:
                logger.error(f"PDF okuma hatası: {e}")
                text_result = "" # Hata olsa bile devam etsin
        else:
            # Resim ise direkt oku
            text_result = pytesseract.image_to_string(Image.open(file_path), lang='tur')

        # 5. TEMİZLİK (Kişisel Veri Bırakma)
        if os.path.exists(file_path):
            os.remove(file_path) 
        
        if not text_result.strip():
            return {"error": "Dosyadan metin okunamadı. Resim çok bulanık olabilir."}

        return {"text": text_result.strip()}

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"OCR Sistem Hatası: {str(e)}")
        return {"error": "Sistem hatası oluştu, dosya okunamadı."}