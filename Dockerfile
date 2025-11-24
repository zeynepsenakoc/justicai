# Python 3.12 Slim (Hafif) İmajı Kullan
FROM python:3.12-slim

# 1. Gerekli Sistem Kütüphanelerini Kur
# Tesseract (OCR), Poppler (PDF İşleme) ve Grafik kütüphaneleri
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizinini ayarla
WORKDIR /app

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright (PDF Motoru) için tarayıcıları kur
RUN playwright install chromium
RUN playwright install-deps

# Proje dosyalarını kopyala
COPY . .

# 2. Uygulamayı Başlat (Gunicorn ile)
# Render 5000 portunu beklemese de standart olarak belirtiyoruz
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]