FROM python:3.12-slim


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1


RUN set -e && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tur \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt


RUN playwright install chromium --with-deps


COPY . .


CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "1", "app:app"]