# Python 3.12 Slim (En Hafif Sürüm)
FROM python:3.12-slim

# Bellek tasarrufu için ayarlar
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# 1. Sistem Kütüphanelerini Kur (Hata verirse devam etmemesi için 'set -e')
# DÜZELTME: 'libgl1-mesa-glx' yerine 'libgl1' yazıldı.
RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tur \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# 2. Önce sadece requirements'ı kopyala ve kur (Cache avantajı)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 3. Playwright'ı en hafif haliyle kur (Sadece Chromium)
RUN playwright install chromium --with-deps

# 4. Kalan dosyaları kopyala
COPY . .

# 5. Başlat (Zaman aşımı süresini 120 saniyeye çıkardık)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "1", "app:app"]