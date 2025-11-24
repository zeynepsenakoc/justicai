import os
import uuid
import logging
import pytesseract
import filetype
from pdf2image import convert_from_path
from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'application/pdf']
MAX_FILE_SIZE = 16 * 1024 * 1024  

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def is_file_safe(file_path):
    try:
        kind = filetype.guess(file_path)
        if kind is None: return False
        if kind.mime not in ALLOWED_MIME_TYPES: return False
        return True
    except Exception as e:
        logger.error(f"Dosya kontrol hatası: {e}")
        return False

def extract_text_from_file(file_storage):
    # Güvenli dosya adı oluştur
    ext = os.path.splitext(file_storage.filename)[1].lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        file_storage.save(file_path)
        
        # 1. Boyut Kontrolü
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            os.remove(file_path)
            return {
                "error": "Dosya çok büyük (Max 16MB).",
                "suggestion": "Lütfen dosya boyutunu küçültüp tekrar deneyin veya PDF sayfalarını ayırın."
            }
            
        # 2. Format/Güvenlik Kontrolü
        if not is_file_safe(file_path):
            os.remove(file_path)
            return {
                "error": "Geçersiz veya desteklenmeyen format.",
                "suggestion": "Sadece JPG, PNG veya PDF formatında dosyalar yükleyiniz."
            }

        text_result = ""
        
        # 3. OCR İşlemi
        if file_path.endswith('.pdf'):
            try:
                pages = convert_from_path(file_path)
                for page in pages:
                    text_result += pytesseract.image_to_string(page, lang='tur') + "\n"
            except Exception as e:
                logger.error(f"PDF Okuma Hatası: {e}")
                # PDF bozuksa bile devam etme, hata dön
                if os.path.exists(file_path): os.remove(file_path)
                return {"error": "PDF dosyası okunamadı.", "suggestion": "Dosya şifreli veya bozuk olabilir. Ekran görüntüsü alıp yüklemeyi deneyin."}
        else:
            try:
                text_result = pytesseract.image_to_string(Image.open(file_path), lang='tur')
            except UnidentifiedImageError:
                if os.path.exists(file_path): os.remove(file_path)
                return {"error": "Görüntü dosyası bozuk.", "suggestion": "Farklı bir formatta (JPG/PNG) tekrar deneyin."}

        # Temizlik
        if os.path.exists(file_path): os.remove(file_path)
        
        # 4. Boş Metin Kontrolü
        if not text_result.strip():
            return {
                "error": "Belgeden okunabilir bir metin çıkarılamadı.",
                "suggestion": "Resim çok bulanık, karanlık veya el yazısı içeriyor olabilir. Lütfen daha net bir fotoğraf yükleyin veya metni elle yazın."
            }

        return {"text": text_result.strip()}

    except Exception as e:
        # Beklenmeyen genel hata
        if os.path.exists(file_path): os.remove(file_path)
        logger.error(f"Kritik OCR Hatası: {e}")
        return {
            "error": "Sistem hatası oluştu.",
            "suggestion": "Lütfen daha sonra tekrar deneyiniz veya teknik destek ile iletişime geçiniz."
        }